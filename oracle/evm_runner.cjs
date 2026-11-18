"use strict";

// Generic, case-independent execution-oracle driver.
//
// Reads a declarative scenario from ORACLE_DRIVER_SPEC, connects to a local
// Anvil node (ORACLE_RPC_URL), deploys contracts from compiled artifacts by
// ABI, submits one honest transaction, then applies the mutation operators
// mechanically and judges each mutated transaction against the policy. No
// per-case JavaScript is loaded; everything comes from the manifest/policy.

const fs = require("fs");
const path = require("path");
const ethers = require("ethers");

// BN254 scalar field modulus r (snarkjs/groth16 public-signal field).
const FIELD_R =
  21888242871839275222246405745257275088548364400416034343698204186575808495617n;

// Deterministic Anvil/Hardhat dev mnemonic. Owned synthetic accounts only.
const DEV_MNEMONIC =
  "test test test test test test test test test test test junk";

const TRANSFER_TOPIC = ethers.id("Transfer(address,address,uint256)");
const ZERO = "0x0000000000000000000000000000000000000000";

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function jsonSafe(value) {
  return JSON.parse(
    JSON.stringify(value, (_, item) =>
      typeof item === "bigint" ? item.toString() : item
    )
  );
}

// ---- artifact loading (Hardhat and Foundry shapes) ------------------------

function findArtifact(name, dirs) {
  for (const dir of dirs) {
    const hit = searchArtifact(name, dir);
    if (hit) return hit;
  }
  throw new Error(`artifact not found for ${name} in ${dirs.join(", ")}`);
}

function searchArtifact(name, dir) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch (_) {
    return null;
  }
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      const hit = searchArtifact(name, full);
      if (hit) return hit;
    } else if (entry.name === `${name}.json`) {
      const data = readJson(full);
      const abi = data.abi;
      let bytecode =
        data.bytecode && data.bytecode.object
          ? data.bytecode.object // Foundry
          : data.bytecode; // Hardhat
      if (abi && bytecode && bytecode !== "0x") {
        return { abi, bytecode };
      }
    }
  }
  return null;
}

// ---- groth16 proof reshaping ----------------------------------------------

function loadProof(entry) {
  const proof = readJson(entry.proof);
  const pub = readJson(entry.public);
  return {
    a: [proof.pi_a[0], proof.pi_a[1]],
    b: [
      [proof.pi_b[0][1], proof.pi_b[0][0]],
      [proof.pi_b[1][1], proof.pi_b[1][0]],
    ],
    c: [proof.pi_c[0], proof.pi_c[1]],
    pub: pub.map((value) => BigInt(value).toString()),
  };
}

// ---- value-expression resolver --------------------------------------------

class Resolver {
  constructor(ctx) {
    this.ctx = ctx; // {signers, deployments, proofs, now}
  }

  resolve(expr) {
    if (Array.isArray(expr)) return expr.map((item) => this.resolve(item));
    if (expr === null || typeof expr !== "object") return expr; // bare literal
    const keys = Object.keys(expr);
    if (keys.length !== 1 || !keys[0].startsWith("$")) {
      // plain object literal (rare) -> resolve values
      const out = {};
      for (const [k, v] of Object.entries(expr)) out[k] = this.resolve(v);
      return out;
    }
    const key = keys[0];
    const arg = expr[key];
    switch (key) {
      case "$lit":
        return arg;
      case "$uint":
        return BigInt(arg);
      case "$bytes":
        return arg;
      case "$signer":
        return this.signer(arg).address;
      case "$addr":
        return this.deployment(arg).target;
      case "$keccakUtf8":
        return ethers.keccak256(ethers.toUtf8Bytes(arg));
      case "$proofPart": {
        const p = this.proof(arg.proof);
        return p[arg.part];
      }
      case "$pubArray":
        return this.proof(arg.proof).pub;
      case "$pub":
        return this.proof(arg.proof).pub[arg.index];
      case "$pubAsBytes32":
        return ethers.toBeHex(BigInt(this.proof(arg.proof).pub[arg.index]), 32);
      case "$pubAsAddress": {
        const raw = BigInt(this.proof(arg.proof).pub[arg.index]);
        return ethers.getAddress(
          "0x" + (raw & ((1n << 160n) - 1n)).toString(16).padStart(40, "0")
        );
      }
      case "$nowPlus":
        return this.ctx.now + Number(arg);
      case "$nowMinus":
        return this.ctx.now - Number(arg);
      case "$tuple":
        return arg.map((item) => this.resolve(item));
      case "$emptyArray":
        return [];
      default:
        throw new Error(`unknown value expression ${key}`);
    }
  }

  signer(name) {
    const s = this.ctx.signers[name];
    if (!s) throw new Error(`unknown signer ${name}`);
    return s;
  }
  deployment(name) {
    const d = this.ctx.deployments[name];
    if (!d) throw new Error(`unknown deployment ${name}`);
    return d;
  }
  proof(name) {
    const p = this.ctx.proofs[name];
    if (!p) throw new Error(`unknown proof ${name}`);
    return p;
  }
}

// ---- effect observation ----------------------------------------------------

function extractEffects(receipt, deploymentsByAddr) {
  const effects = [];
  for (const log of receipt.logs || []) {
    if (!log.topics || log.topics[0] !== TRANSFER_TOPIC) continue;
    const contractAddr = log.address.toLowerCase();
    const role = deploymentsByAddr[contractAddr] || null;
    if (log.topics.length === 4) {
      effects.push({
        kind: "erc721_transfer",
        contract: log.address,
        contract_role: role,
        from: ethers.getAddress("0x" + log.topics[1].slice(26)),
        to: ethers.getAddress("0x" + log.topics[2].slice(26)),
        token_id: BigInt(log.topics[3]).toString(),
      });
    } else if (log.topics.length === 3) {
      effects.push({
        kind: "erc20_transfer",
        contract: log.address,
        contract_role: role,
        from: ethers.getAddress("0x" + log.topics[1].slice(26)),
        to: ethers.getAddress("0x" + log.topics[2].slice(26)),
        value: BigInt(log.data).toString(),
      });
    }
  }
  return effects;
}

function isMint(effect, spec) {
  if (!effect.from) return false;
  if (effect.from.toLowerCase() !== ZERO) return false;
  if (spec.contract_role && effect.contract_role !== spec.contract_role)
    return false;
  if (spec.type && effect.kind !== spec.type) return false;
  return true;
}

// Does an observed effect discharge a declared required obligation (S4c)? An
// obligation match names the kind of committed effect that an authorization must
// produce alongside its benefit (e.g. a fee transfer to the treasury, or a
// nullifier-marking mint). `to` is a value expression resolved to the required
// recipient. All checks are over already-observed local effects; nothing is
// queried off-chain.
function matchesObligation(effect, match, resolver) {
  if (match.type && effect.kind !== match.type) return false;
  if (match.from === "0x0") {
    if (!effect.from || effect.from.toLowerCase() !== ZERO) return false;
  }
  if (match.contract_role && effect.contract_role !== match.contract_role)
    return false;
  if (match.to) {
    const want = String(resolver.resolve(match.to)).toLowerCase();
    if (!effect.to || effect.to.toLowerCase() !== want) return false;
  }
  return true;
}

// ---- policy evaluation -----------------------------------------------------

async function evaluatePolicy(policy, effects, context, resolver, contractsByAddr) {
  const violations = [];
  for (const rule of policy.protected_effects || []) {
    const matched = effects.filter((e) => isMint(e, rule.match || {}));
    for (const effect of matched) {
      for (const ent of rule.entitlements || []) {
        const expected = resolver.resolve(ent.equals);
        let observed;
        if (ent.field) {
          observed = effect[ent.field];
        } else if (ent.view) {
          // Query the instance that EMITTED the effect (by address), not a
          // fixed name, so a DOMAIN second instance is read correctly.
          const contract = contractsByAddr[effect.contract.toLowerCase()];
          if (!contract) {
            observed = "<no contract instance for effect address>";
          } else {
            const args = (ent.view.args || []).map((a) =>
              a === "$tokenId" ? effect.token_id : resolver.resolve(a)
            );
            observed = await contract[ent.view.function](...args);
          }
        }
        if (
          String(observed).toLowerCase() !== String(expected).toLowerCase()
        ) {
          violations.push({
            rule: rule.id,
            type: "entitlement_mismatch",
            check: ent.field ? `effect.${ent.field}` : `view ${ent.view.function}`,
            observed: String(observed),
            expected: String(expected),
          });
        }
      }
    }
    if (rule.single_use && context.single_use_double_spend) {
      violations.push({
        rule: rule.id,
        type: "single_use_exceeded",
        authorization_key: context.authorization_key,
        occurrences: 2,
        max_occurrences: 1,
      });
    }
  }

  // Undischarged required obligations (S4c): an authorization that grants the
  // protected benefit must also commit each required obligation. If the honest
  // path discharged the obligation but this mutated tx granted the benefit while
  // omitting it, the required effect went undischarged — a violation of a
  // different shape from an unauthorized effect. Conditioning on the honest
  // path's own behaviour avoids flagging an obligation the real path never
  // produces (which would overclaim).
  for (const obl of policy.required_obligations || []) {
    const dischargedHere = effects.some((e) =>
      matchesObligation(e, obl.match || {}, resolver)
    );
    const dischargedHonest = (context.honest_obligations || []).includes(obl.id);
    if (context.benefit_committed && dischargedHonest && !dischargedHere) {
      violations.push({
        rule: obl.id,
        type: "undischarged_obligation",
        obligation: obl.id,
        description: obl.description || null,
        discharged_by_honest: true,
        discharged_by_mutation: false,
      });
    }
  }
  return violations;
}

// Canonical single-use key: the policy's pub position reduced mod r.
function authorizationKey(policy, pubArrayByProof) {
  for (const rule of policy.protected_effects || []) {
    if (rule.single_use) {
      const src = rule.single_use.key_pub;
      const pub = pubArrayByProof[src.proof];
      if (!pub) return null;
      return (BigInt(pub[src.index]) % FIELD_R).toString();
    }
  }
  return null;
}

// ---- transaction plumbing --------------------------------------------------

async function deployAll(spec, resolver, provider, deployScript) {
  const deployments = {};
  const deploymentsByAddr = {};
  resolver.ctx.deployments = deployments;
  for (const step of deployScript) {
    const art = findArtifact(step.artifact, spec.artifacts_dirs);
    const from = resolver.signer(step.from || spec.scenario.deployer || spec.scenario.signers[0]);
    const factory = new ethers.ContractFactory(art.abi, art.bytecode, from);
    const args = (step.args || []).map((a) => resolver.resolve(a));
    // Fixed gasLimit skips eth_estimateGas on deploys, which can transiently
    // fail with "missing revert data" against a busy local node. Deploys never
    // revert here, so a high fixed limit (well under Anvil's 30M block limit) is
    // safe and deterministic.
    const contract = await factory.deploy(...args, {
      nonce: await nextNonce(from),
      gasLimit: 20000000n,
    });
    await contract.waitForDeployment();
    const target = await contract.getAddress();
    deployments[step.name] = { contract, target, abi: art.abi };
    deploymentsByAddr[target.toLowerCase()] = step.name;
  }
  return { deployments, deploymentsByAddr };
}

function buildArgs(argSpecs, resolver, overrides) {
  return argSpecs.map((arg) => {
    if (overrides && Object.prototype.hasOwnProperty.call(overrides, arg.name)) {
      return resolver.resolve(overrides[arg.name]);
    }
    return resolver.resolve(arg.value);
  });
}

// Explicit, sequential nonce: every write awaits the prior one, so the mined
// ("latest") count is the correct next nonce. This removes "nonce has already
// been used" races from the provider's pending cache on a busy local node.
async function nextNonce(signer) {
  return signer.getNonce("latest");
}

async function sendTx(deployment, func, args, signer, value) {
  const connected = deployment.contract.connect(signer);
  try {
    const overrides = { nonce: await nextNonce(signer) };
    if (value) overrides.value = value;
    const tx = await connected[func](...args, overrides);
    const receipt = await tx.wait();
    return { succeeded: receipt.status === 1, hash: tx.hash, receipt, error: null };
  } catch (error) {
    return {
      succeeded: false,
      hash: error?.transaction?.hash || error?.receipt?.hash || null,
      receipt: error?.receipt || null,
      error: String(error.shortMessage || error.reason || error.message || error),
    };
  }
}

async function trace(provider, hash) {
  if (!hash) return null;
  try {
    return await provider.send("debug_traceTransaction", [
      hash,
      { tracer: "prestateTracer", tracerConfig: { diffMode: true } },
    ]);
  } catch (error) {
    return { trace_error: String(error.message || error) };
  }
}

// Verify the proof is accepted by the UNCHANGED verifier contract directly.
async function verifierAccepts(scenario, deployments, resolver) {
  const checks = scenario.verifier_checks || [];
  const results = [];
  for (const check of checks) {
    const dep = deployments[check.contract];
    const args = check.args.map((a) => resolver.resolve(a));
    try {
      const ok = await dep.contract[check.function](...args);
      results.push({ contract: check.contract, accepted: Boolean(ok) });
    } catch (error) {
      results.push({ contract: check.contract, accepted: false, error: String(error.message || error) });
    }
  }
  const accepted = results.length > 0 && results.every((r) => r.accepted);
  return { accepted, results };
}

// ---- one trial -------------------------------------------------------------

async function runTrial(env, trial) {
  const { spec, provider, signers, proofs, baseDeploy } = env;
  const scenario = spec.scenario;
  const now = Number((await provider.getBlock("latest")).timestamp);
  const resolver = new Resolver({ signers, deployments: {}, proofs, now });

  // Fresh deployment per trial for isolation (so REPLAY/ALIAS/DOMAIN preludes
  // do not leak into other operators).
  let deployScript = baseDeploy;
  const { deployments, deploymentsByAddr } = await deployAll(spec, resolver, provider, deployScript);
  for (const step of scenario.post_deploy || []) {
    const dep = deployments[step.target];
    const from = resolver.signer(step.from);
    const args = (step.args || []).map((a) => resolver.resolve(a));
    const r = await sendTx(dep, step.function, args, from, null);
    if (!r.succeeded) {
      return { ...trial, result: "UNKNOWN", reason: `post_deploy ${step.function} reverted: ${r.error}` };
    }
  }

  // Admitted initial state (S4b): manifest-declared setup applied on the owned
  // local chain before any honest/mutated call, so a confirmed effect's
  // magnitude is measured against a non-trivial baseline, not a blank chain.
  const admittedInitialState = [];
  for (const step of scenario.initial_state || []) {
    const dep = deployments[step.target];
    const from = resolver.signer(step.from);
    const args = (step.args || []).map((a) => resolver.resolve(a));
    const r = await sendTx(dep, step.function, args, from, step.value ? resolver.resolve(step.value) : null);
    admittedInitialState.push({ target: step.target, function: step.function, applied: r.succeeded, error: r.error });
    if (!r.succeeded) {
      return { ...trial, result: "UNKNOWN", reason: `initial_state ${step.function} reverted: ${r.error}` };
    }
  }

  const va = await verifierAccepts(scenario, deployments, resolver);

  const honest = scenario.honest_tx;
  const honestFrom = resolver.signer(honest.from);
  const honestValue = honest.value ? resolver.resolve(honest.value) : null;

  // optional prelude (consumes the honest authorization once)
  let prelude = null;
  let authKey = authorizationKey(spec.policy, { [Object.keys(proofs)[0]]: null }) ; // placeholder
  const pubByProof = {};
  for (const [name, p] of Object.entries(proofs)) pubByProof[name] = p.pub;
  authKey = authorizationKey(spec.policy, pubByProof);

  if (trial.prelude_honest) {
    const args = buildArgs(honest.args, resolver, null);
    prelude = await sendTx(deployments[honest.target], honest.function, args, honestFrom, honestValue);
    if (!prelude.succeeded) {
      return { ...trial, result: "UNKNOWN", reason: `honest prelude reverted: ${prelude.error}`, verifier_accepted: va.accepted };
    }
  }

  // Build the mutated invocation
  let target = deployments[honest.target];
  let from = honestFrom;
  let overrides = null;
  let aliasNote = null;
  const domainContracts = {}; // address -> contract, for DOMAIN second instance

  if (trial.operator === "CALLER") {
    from = resolver.signer(trial.caller);
  } else if (trial.operator === "FREE_ARG") {
    overrides = { [trial.arg]: scenario.free_args[trial.arg].mutation };
  } else if (trial.operator === "ALIAS") {
    const aliasArg = scenario.alias.arg;
    const base = resolver.resolve(honest.args.find((a) => a.name === aliasArg).value).slice();
    base[trial.position] = (BigInt(base[trial.position]) + FIELD_R).toString();
    overrides = { [aliasArg]: { $lit: base } };
    aliasNote = { arg: aliasArg, position: trial.position };
  } else if (trial.operator === "DOMAIN") {
    // Redeploy a second, independent instance of the consumer group and submit
    // the same honest proof there. deployAll repoints resolver.ctx.deployments
    // to the second instance (plain names), so post_deploy args resolve against
    // it. The second instance's effects are still observed (merged by address).
    const domainScript = scenario.domain.redeploy.map((n) => baseDeploy.find((d) => d.name === n));
    const second = await deployAll(spec, resolver, provider, domainScript);
    for (const [addr, name] of Object.entries(second.deploymentsByAddr)) {
      deploymentsByAddr[addr] = "domain2_" + name;
    }
    for (const step of scenario.domain.post_deploy || []) {
      const dep = second.deployments[step.target];
      const f = resolver.signer(step.from);
      const a = (step.args || []).map((x) => resolver.resolve(x));
      const r = await sendTx(dep, step.function, a, f, null);
      if (!r.succeeded) {
        return { ...trial, result: "UNKNOWN", reason: `domain post_deploy ${step.function} reverted: ${r.error}` };
      }
    }
    for (const dep of Object.values(second.deployments)) {
      domainContracts[dep.target.toLowerCase()] = dep.contract;
    }
    target = second.deployments[honest.target];
  }
  // REPLAY: identical honest tx (no overrides), target unchanged.

  const contractsByAddr = {};
  for (const dep of Object.values(deployments)) {
    contractsByAddr[dep.target.toLowerCase()] = dep.contract;
  }
  Object.assign(contractsByAddr, domainContracts);

  // Value-at-risk (S4b): snapshot token supply and signer balances immediately
  // before the mutated tx (i.e. after deploy + initial_state + any prelude) and
  // again after, so the committed magnitude is exact and signed.
  const valueBefore = await snapshotValues(contractsByAddr, signers);

  // `overrides` maps argName -> value expression; buildArgs resolves them.
  const args = buildArgs(honest.args, resolver, overrides);
  const settled = await sendTx(target, honest.function, args, from, honestValue);
  const stateDiff = await trace(provider, settled.hash);
  const valueAfter = await snapshotValues(contractsByAddr, signers);
  const valueAtRisk = {
    admitted_initial_state: admittedInitialState,
    deltas: valueDeltas(valueBefore, valueAfter),
  };

  const effects = settled.succeeded ? extractEffects(settled.receipt, deploymentsByAddr) : [];

  // single-use double-spend detection
  let doubleSpend = false;
  if (trial.prelude_honest && settled.succeeded && effects.some((e) => isMintAny(e, spec.policy))) {
    // the honest prelude already consumed authKey; a second committed mint
    // under the same canonical key is a double spend
    doubleSpend = true;
  }

  const benefitCommitted = effects.some((e) => isMintAny(e, spec.policy));
  const context = {
    authorization_key: authKey,
    single_use_double_spend: doubleSpend,
    mutated_sender: from.address,
    honest_obligations: env.honestObligations || [],
    benefit_committed: benefitCommitted,
  };
  const violations = settled.succeeded
    ? await evaluatePolicy(spec.policy, effects, context, resolver, contractsByAddr)
    : [];

  // Per-trial obligation ledger (S4c): for each declared required obligation,
  // whether the honest reference discharged it and whether this mutated tx did.
  const obligations = (spec.policy.required_obligations || []).map((obl) => ({
    id: obl.id,
    description: obl.description || null,
    discharged_by_honest: (env.honestObligations || []).includes(obl.id),
    discharged_by_mutation: effects.some((e) =>
      matchesObligation(e, obl.match || {}, resolver)
    ),
  }));

  // Signed magnitude per protected effect: ERC-20 value, or one unit per ERC-721
  // token id. Direction is + (value created for / routed to the recipient).
  for (const effect of effects) {
    effect.magnitude = effect.kind === "erc20_transfer" ? effect.value : "1";
    effect.magnitude_unit = effect.kind === "erc20_transfer" ? "token-wei" : "nft-unit";
  }
  valueAtRisk.effects = effects.map((e) => ({
    contract: e.contract,
    kind: e.kind,
    recipient: e.to,
    token_id: e.token_id,
    magnitude: e.magnitude,
    magnitude_unit: e.magnitude_unit,
  }));

  let result;
  let reason;
  if (!settled.succeeded) {
    result = "NOT_CONFIRMED";
    reason = `reverted: ${settled.error}`;
  } else if (effects.length === 0) {
    result = "NOT_CONFIRMED";
    reason = "effects identical (no protected effect committed)";
  } else if (violations.length === 0) {
    result = "NOT_CONFIRMED";
    reason = "policy-permitted";
  } else if (!va.accepted) {
    result = "UNKNOWN";
    reason = "verifier acceptance not established";
  } else {
    result = "E4-CONFIRMED";
    reason = "mutated tx succeeded through unchanged verifier+consumer and committed a policy violation";
  }

  return jsonSafe({
    ...trial,
    result,
    reason,
    verifier_accepted: va.accepted,
    verifier_checks: va.results,
    tx_succeeded: settled.succeeded,
    tx_hash: settled.hash,
    tx_error: settled.error,
    mutated_sender: from.address,
    alias: aliasNote,
    prelude: prelude ? { succeeded: prelude.succeeded, hash: prelude.hash } : null,
    protected_effects: effects,
    policy_violations: violations,
    obligations,
    value_at_risk: valueAtRisk,
    authorization_key: authKey,
    events: settled.receipt ? settled.receipt.logs.map((l) => ({ address: l.address, topics: l.topics, data: l.data })) : [],
    state_diff: stateDiff,
  });
}

function isMintAny(effect, policy) {
  for (const rule of policy.protected_effects || []) {
    if (isMint(effect, rule.match || {})) return true;
  }
  return false;
}

// ---- value-at-risk observation (S4b) ---------------------------------------

// Snapshot totalSupply and each named signer's balanceOf on every token-like
// contract. Read-only; owned local chain only. ERC-721 balanceOf returns a
// holdings count; ERC-20 returns a token amount. Missing views are skipped.
async function snapshotValues(contractsByAddr, signers) {
  const snap = {};
  for (const [addr, contract] of Object.entries(contractsByAddr)) {
    let total = null;
    try {
      total = (await contract.totalSupply()).toString();
    } catch (_) {
      /* not a supply-bearing token */
    }
    const balances = {};
    for (const [name, wallet] of Object.entries(signers)) {
      try {
        balances[name] = (await contract.balanceOf(wallet.address)).toString();
      } catch (_) {
        /* no balanceOf */
      }
    }
    if (total !== null || Object.keys(balances).length) {
      snap[addr] = { total_supply: total, balances };
    }
  }
  return snap;
}

// Signed deltas between two value snapshots (after - before).
function valueDeltas(before, after) {
  const deltas = {};
  for (const addr of new Set([...Object.keys(before), ...Object.keys(after)])) {
    const b = before[addr] || { total_supply: null, balances: {} };
    const a = after[addr] || { total_supply: null, balances: {} };
    let supplyDelta = null;
    if (a.total_supply !== null && b.total_supply !== null) {
      supplyDelta = (BigInt(a.total_supply) - BigInt(b.total_supply)).toString();
    }
    const balanceDeltas = {};
    for (const name of new Set([...Object.keys(b.balances), ...Object.keys(a.balances)])) {
      const bv = BigInt(b.balances[name] ?? "0");
      const av = BigInt(a.balances[name] ?? "0");
      const d = av - bv;
      if (d !== 0n) balanceDeltas[name] = d.toString();
    }
    if ((supplyDelta !== null && supplyDelta !== "0") || Object.keys(balanceDeltas).length) {
      deltas[addr] = {
        total_supply_before: b.total_supply,
        total_supply_after: a.total_supply,
        total_supply_delta: supplyDelta,
        balance_deltas: balanceDeltas,
      };
    }
  }
  return deltas;
}

// ---- trial enumeration -----------------------------------------------------

function enumerateTrials(scenario) {
  const trials = [];
  for (const op of scenario.operators) {
    if (op === "CALLER") {
      for (const caller of scenario.caller_candidates || []) {
        trials.push({ operator: "CALLER", id: `CALLER-${caller}`, caller, prelude_honest: false });
      }
    } else if (op === "FREE_ARG") {
      for (const arg of Object.keys(scenario.free_args || {})) {
        trials.push({ operator: "FREE_ARG", id: `FREE_ARG-${arg}`, arg, prelude_honest: false });
      }
    } else if (op === "ALIAS") {
      for (const position of scenario.alias.positions) {
        trials.push({ operator: "ALIAS", id: `ALIAS-${position}`, position, prelude_honest: true });
      }
    } else if (op === "REPLAY") {
      trials.push({ operator: "REPLAY", id: "REPLAY", prelude_honest: true });
    } else if (op === "DOMAIN") {
      trials.push({ operator: "DOMAIN", id: "DOMAIN", prelude_honest: false });
    }
  }
  return trials;
}

// ---- replay bundle ---------------------------------------------------------

function writeReplayBundle(spec, trial) {
  if (trial.result !== "E4-CONFIRMED") return null;
  const slug = `${spec.variant.id}-${trial.id}`.replace(/[^a-zA-Z0-9_.-]/g, "-");
  const dir = path.join(spec.output_dir, "replay-bundles", slug);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(spec.manifest_path, path.join(dir, "manifest.json"));
  fs.copyFileSync(spec.policy_path, path.join(dir, "policy.json"));
  fs.writeFileSync(path.join(dir, "result.json"), JSON.stringify(trial, null, 2) + "\n");
  const run =
    "#!/usr/bin/env bash\nset -euo pipefail\n" +
    'ROOT="$(git rev-parse --show-toplevel)"\n' +
    `exec python3 -m oracle run "${spec.manifest_path}" --out "$ROOT/results/raw/S4/replay-${slug}-$(date -u +%Y%m%dT%H%M%SZ)"\n`;
  fs.writeFileSync(path.join(dir, "run.sh"), run, { mode: 0o755 });
  return dir;
}

// ---- main ------------------------------------------------------------------

async function main() {
  const spec = readJson(process.env.ORACLE_DRIVER_SPEC);
  const provider = new ethers.JsonRpcProvider(
    process.env.ORACLE_RPC_URL,
    undefined,
    { staticNetwork: true }
  );
  await provider.ready;

  const scenario = spec.scenario;
  const signers = {};
  scenario.signers.forEach((name, index) => {
    const wallet = ethers.HDNodeWallet.fromPhrase(
      DEV_MNEMONIC,
      "",
      `m/44'/60'/0'/0/${index}`
    ).connect(provider);
    signers[name] = wallet;
  });

  const proofs = {};
  for (const [name, entry] of Object.entries(scenario.proofs || {})) {
    proofs[name] = loadProof(entry);
  }

  const baseDeploy = scenario.deploy;
  const env = { spec, provider, signers, proofs, baseDeploy };

  // honest reference run (its own isolated deployment)
  const honestResolver = new Resolver({
    signers,
    deployments: {},
    proofs,
    now: Number((await provider.getBlock("latest")).timestamp),
  });
  const honestDeploy = await deployAll(spec, honestResolver, provider, baseDeploy);
  for (const step of [...(scenario.post_deploy || []), ...(scenario.initial_state || [])]) {
    const dep = honestDeploy.deployments[step.target];
    const from = honestResolver.signer(step.from);
    const args = (step.args || []).map((a) => honestResolver.resolve(a));
    await sendTx(dep, step.function, args, from, step.value ? honestResolver.resolve(step.value) : null);
  }
  const honestVa = await verifierAccepts(scenario, honestDeploy.deployments, honestResolver);
  const honestArgs = buildArgs(scenario.honest_tx.args, honestResolver, null);
  const honestSettled = await sendTx(
    honestDeploy.deployments[scenario.honest_tx.target],
    scenario.honest_tx.function,
    honestArgs,
    honestResolver.signer(scenario.honest_tx.from),
    scenario.honest_tx.value ? honestResolver.resolve(scenario.honest_tx.value) : null
  );
  const honestEffects = honestSettled.succeeded
    ? extractEffects(honestSettled.receipt, honestDeploy.deploymentsByAddr)
    : [];
  // Required obligations the honest path actually discharges (S4c). A mutated
  // trial can only be faulted for *omitting* an obligation the honest path
  // itself commits, so this set is the reference the oracle conditions on.
  const honestObligations = [];
  for (const obl of spec.policy.required_obligations || []) {
    if (honestEffects.some((e) => matchesObligation(e, obl.match || {}, honestResolver))) {
      honestObligations.push(obl.id);
    }
  }
  env.honestObligations = honestObligations;

  const honest = jsonSafe({
    succeeded: honestSettled.succeeded,
    verifier_accepted: honestVa.accepted,
    verifier_checks: honestVa.results,
    tx_hash: honestSettled.hash,
    error: honestSettled.error,
    protected_effects: honestEffects,
    obligations_discharged: honestObligations,
  });

  const trials = [];
  for (const trial of enumerateTrials(scenario)) {
    const t0 = process.hrtime.bigint();
    let result;
    try {
      result = await runTrial(env, trial);
    } catch (error) {
      result = { ...trial, result: "UNKNOWN", reason: `driver error: ${String(error.message || error)}` };
    }
    result.wall_seconds = Number(process.hrtime.bigint() - t0) / 1e9;
    result.replay_bundle = writeReplayBundle(spec, result);
    trials.push(result);
  }

  const operatorWall = {};
  for (const t of trials) {
    operatorWall[t.operator] = (operatorWall[t.operator] || 0) + (t.wall_seconds || 0);
  }

  const out = {
    schema_version: 1,
    case_id: spec.case_id,
    variant: spec.variant.id,
    local_rpc: "127.0.0.1",
    fork_enabled: false,
    honest,
    honest_succeeded: honest.succeeded,
    trials,
    operator_wall_seconds: operatorWall,
  };
  fs.writeFileSync(spec.result_path, JSON.stringify(out, null, 2) + "\n");
  if (!honest.succeeded) process.exitCode = 3;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 2;
});

module.exports = { FIELD_R, extractEffects, evaluatePolicy, matchesObligation };
