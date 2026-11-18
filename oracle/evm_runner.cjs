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
// Load the pinned ethers explicitly. NODE_PATH alone is not enough: node
// resolves a `node_modules/ethers` in an ancestor of the cwd (e.g. a repo-root
// install pulled in by snarkjs) before NODE_PATH, which can shadow the pinned
// 6.x with an incompatible 5.x. runner.py sets ORACLE_ETHERS_PATH.
const ethers = require(process.env.ORACLE_ETHERS_PATH || "ethers");

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
      case "$signerUint":
        // A signer address as a uint256 (for row-owner fields encoded as uint).
        return BigInt(this.signer(arg).address);
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
  // XR-07: an obligation may fix the quantity. A fee of +1 does not discharge a
  // required fee of +50. ERC-721 obligations may fix the token id instead.
  if (match.value !== undefined && match.value !== null) {
    const want = String(resolver.resolve(match.value));
    if (effect.value === undefined || String(effect.value) !== want) return false;
  }
  if (match.token_id !== undefined && match.token_id !== null) {
    const want = String(resolver.resolve(match.token_id));
    if (effect.token_id === undefined || String(effect.token_id) !== want) return false;
  }
  return true;
}

// XR-07: occurrence-preserving count of effects discharging an obligation. A
// single matching event must not satisfy two required obligations of the same
// shape, so discharge is scored as a multiset: the mutated count must reach the
// honest count.
function obligationCount(effects, match, resolver) {
  let n = 0;
  for (const e of effects) if (matchesObligation(e, match, resolver)) n += 1;
  return n;
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
  const honestCounts = context.honest_obligations || {};
  for (const obl of policy.required_obligations || []) {
    const honestN = honestCounts[obl.id] || 0;
    const hereN = obligationCount(effects, obl.match || {}, resolver);
    // Undischarged iff the honest path discharged it to multiplicity honestN,
    // this tx granted the benefit, and it reaches fewer than honestN here (XR-07:
    // a wrong amount or missing occurrence counts as undischarged).
    if (context.benefit_committed && honestN > 0 && hereN < honestN) {
      violations.push({
        rule: obl.id,
        type: "undischarged_obligation",
        obligation: obl.id,
        description: obl.description || null,
        required_occurrences: honestN,
        observed_occurrences: hereN,
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
      nonce: await allocNonce(from),
      gasLimit: 20000000n,
    });
    bumpNonce(from);
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

// Local per-signer nonce counter. Querying the node for every write (even with
// "pending") races on a busy local node when several sends happen in quick
// succession (e.g. a DOMAIN second-instance deploy burst), producing "nonce has
// already been used". Instead we seed each signer's nonce once from the node and
// advance it locally: `allocNonce` hands out the next nonce, `bumpNonce` is
// called only after a tx is actually broadcast (so a tx that reverts at gas
// estimation, before broadcast, does not consume one), and `resyncNonce`
// re-reads the node after any failure to recover exactly.
const _nonces = new Map();
async function allocNonce(signer) {
  const addr = signer.address;
  if (!_nonces.has(addr)) {
    _nonces.set(addr, Number(await signer.getNonce("pending")));
  }
  return _nonces.get(addr);
}
function bumpNonce(signer) {
  const addr = signer.address;
  if (_nonces.has(addr)) _nonces.set(addr, _nonces.get(addr) + 1);
}
async function resyncNonce(signer) {
  _nonces.set(signer.address, Number(await signer.getNonce("pending")));
}

async function sendTx(deployment, func, args, signer, value) {
  const connected = deployment.contract.connect(signer);
  try {
    const overrides = { nonce: await allocNonce(signer) };
    if (value) overrides.value = value;
    const tx = await connected[func](...args, overrides);
    bumpNonce(signer); // broadcast succeeded: this nonce is now consumed
    const receipt = await tx.wait();
    return { succeeded: receipt.status === 1, hash: tx.hash, receipt, error: null };
  } catch (error) {
    // A tx that reverts at gas estimation never broadcast, so its nonce is still
    // free; re-read the node to recover the exact next nonce either way.
    await resyncNonce(signer);
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

// Call-level trace of a transaction (XR-02). Used to establish that the
// unchanged verifier contract was actually invoked on the MUTATED execution
// path and returned true, rather than relying on a standalone check of the
// original proof (that standalone check is kept only as an E3 preflight).
async function callTrace(provider, hash) {
  if (!hash) return null;
  try {
    return await provider.send("debug_traceTransaction", [
      hash,
      { tracer: "callTracer" },
    ]);
  } catch (error) {
    return { trace_error: String(error.message || error) };
  }
}

// Flatten a callTracer tree into a list of {to, type, output, error, revert}.
function flattenCalls(node, out) {
  out = out || [];
  if (!node || typeof node !== "object") return out;
  if (node.to) {
    out.push({
      to: String(node.to).toLowerCase(),
      type: node.type || null,
      output: node.output || null,
      error: node.error || null,
      revertReason: node.revertReason || null,
    });
  }
  for (const child of node.calls || []) flattenCalls(child, out);
  return out;
}

// XR-02: did the mutated tx actually call one of the unchanged verifier
// addresses, with that call returning boolean true and not reverting? A Groth16
// `verifyProof`/`verify` returns a 32-byte word; we treat a non-reverting call
// whose output decodes to 1 as acceptance on the mutated path.
function verifierOnMutatedPath(callTree, verifierAddrs) {
  const want = new Set((verifierAddrs || []).map((a) => a.toLowerCase()));
  if (!want.size || !callTree || callTree.trace_error) {
    return { established: false, reason: want.size ? "no_call_trace" : "no_verifier_declared", calls: [] };
  }
  const calls = flattenCalls(callTree, []);
  const hits = calls.filter((c) => want.has(c.to));
  for (const c of hits) {
    if (c.error || c.revertReason) continue;
    let truthy = false;
    try {
      truthy = c.output != null && BigInt(c.output) === 1n;
    } catch (_) {
      truthy = false;
    }
    if (truthy) {
      return { established: true, reason: "verifier_called_true_on_mutated_path", callee: c.to };
    }
  }
  return {
    established: false,
    reason: hits.length ? "verifier_called_but_not_true" : "verifier_not_called_on_mutated_path",
    verifier_calls: hits,
  };
}

// XR-01: corroborate a claimed protected effect against chain STATE, not just
// the emitted event. Reads the recipient's token state immediately before and
// after the mutated tx's block (historical calls on the owned local chain), so
// a bare `Transfer` log with no matching balance/ownership change cannot carry
// an E4. For ERC-20 the recipient balance must rise by exactly the logged value;
// for ERC-721 the recipient must own the logged token id after the tx.
async function corroborateEffect(contract, effect, blockNumber) {
  if (!contract || blockNumber == null) {
    return { corroborated: false, reason: "no_contract_or_block" };
  }
  const before = blockNumber - 1;
  try {
    if (effect.kind === "erc20_transfer") {
      const b = await contract.balanceOf(effect.to, { blockTag: before });
      const a = await contract.balanceOf(effect.to, { blockTag: blockNumber });
      const delta = BigInt(a) - BigInt(b);
      const ok = delta === BigInt(effect.value);
      return {
        corroborated: ok,
        reason: ok ? "balance_delta_matches_value" : "balance_delta_mismatch",
        recipient_balance_before: b.toString(),
        recipient_balance_after: a.toString(),
        recipient_balance_delta: delta.toString(),
        logged_value: effect.value,
      };
    }
    if (effect.kind === "erc721_transfer") {
      const owner = await contract.ownerOf(effect.token_id, { blockTag: blockNumber });
      const ok = String(owner).toLowerCase() === effect.to.toLowerCase();
      return {
        corroborated: ok,
        reason: ok ? "owner_matches_recipient" : "owner_mismatch",
        owner_after: String(owner),
        logged_recipient: effect.to,
      };
    }
  } catch (error) {
    return { corroborated: false, reason: "state_read_failed: " + String(error.shortMessage || error.message || error) };
  }
  return { corroborated: false, reason: "unsupported_effect_kind" };
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
  // Deployment set whose verifier the mutated tx actually runs against (the
  // second instance for DOMAIN). Used to establish the verifier call on the
  // mutated path (XR-02).
  let verifierDeployments = deployments;

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
    verifierDeployments = second.deployments;
  }
  // REPLAY: identical honest tx (no overrides), target unchanged.

  const contractsByAddr = {};
  for (const dep of Object.values(deployments)) {
    contractsByAddr[dep.target.toLowerCase()] = dep.contract;
  }
  Object.assign(contractsByAddr, domainContracts);

  // Deployment set the mutated tx runs against (second instance for DOMAIN).
  const activeDeployments = verifierDeployments;

  // Value-at-risk (S4b): snapshot token supply and signer balances immediately
  // before the mutated tx (i.e. after deploy + initial_state + any prelude) and
  // again after, so the committed magnitude is exact and signed.
  const valueBefore = await snapshotValues(contractsByAddr, signers);
  // View-based state effects (S4d): credit/backing-style counters with no event.
  const viewBefore = await readStateViews(activeDeployments, scenario, resolver);

  // `overrides` maps argName -> value expression; buildArgs resolves them.
  const args = buildArgs(honest.args, resolver, overrides);
  const settled = await sendTx(target, honest.function, args, from, honestValue);
  const stateDiff = await trace(provider, settled.hash);
  const callTree = settled.succeeded ? await callTrace(provider, settled.hash) : null;
  const valueAfter = await snapshotValues(contractsByAddr, signers);
  const viewAfter = await readStateViews(activeDeployments, scenario, resolver);
  const viewDeltas = diffViews(viewBefore, viewAfter);
  const valueAtRisk = {
    admitted_initial_state: admittedInitialState,
    deltas: valueDeltas(valueBefore, valueAfter),
  };

  const effects = settled.succeeded ? extractEffects(settled.receipt, deploymentsByAddr) : [];

  // XR-02: verifier acceptance on the MUTATED call path, from the call trace of
  // the mutated tx itself (not the standalone original-proof preflight `va`).
  const verifierAddrs = (scenario.verifier_checks || [])
    .map((c) => verifierDeployments[c.contract] && verifierDeployments[c.contract].target)
    .filter(Boolean);
  const verifierPath = settled.succeeded
    ? verifierOnMutatedPath(callTree, verifierAddrs)
    : { established: false, reason: "mutated_tx_reverted" };

  // XR-01: corroborate each claimed protected effect against chain state (a
  // recipient balance rise / ownership change at the mutated tx's block). An
  // event with no matching state cannot carry an E4.
  const blockNumber = settled.receipt ? settled.receipt.blockNumber : null;
  for (const effect of effects) {
    if (isMintAny(effect, spec.policy)) {
      const contract = contractsByAddr[effect.contract.toLowerCase()];
      effect.state_corroboration = await corroborateEffect(contract, effect, blockNumber);
    }
  }

  // single-use double-spend detection
  let doubleSpend = false;
  if (trial.prelude_honest && settled.succeeded && effects.some((e) => isMintAny(e, spec.policy))) {
    // the honest prelude already consumed authKey; a second committed mint
    // under the same canonical key is a double spend
    doubleSpend = true;
  }

  // A protected effect may be a transfer mint or a declared view increase (S4d).
  const viewCommitted = settled.succeeded && protectedViewCommitted(spec.policy, viewDeltas);
  const benefitCommitted = effects.some((e) => isMintAny(e, spec.policy)) || viewCommitted;
  const honestCounts = env.honestObligations || {};
  const context = {
    authorization_key: authKey,
    single_use_double_spend: doubleSpend,
    mutated_sender: from.address,
    honest_obligations: honestCounts,
    benefit_committed: benefitCommitted,
  };
  const transferViolations = settled.succeeded
    ? await evaluatePolicy(spec.policy, effects, context, resolver, contractsByAddr)
    : [];
  const viewViolations = settled.succeeded
    ? evaluateViewObligations(spec.policy, viewDeltas, env.honestViewDeltas)
    : [];
  const violations = transferViolations.concat(viewViolations);

  // Per-trial obligation ledger (S4c/XR-07): honest vs mutated occurrence counts.
  const obligations = (spec.policy.required_obligations || []).map((obl) => ({
    id: obl.id,
    description: obl.description || null,
    required_occurrences: honestCounts[obl.id] || 0,
    discharged_by_honest: (honestCounts[obl.id] || 0) > 0,
    observed_occurrences: obligationCount(effects, obl.match || {}, resolver),
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

  // XR-01: a protected effect used to confirm must be state-corroborated. Any
  // mint-shaped protected effect with no matching state read is disqualifying.
  const uncorroborated = effects.filter(
    (e) => e.state_corroboration && e.state_corroboration.corroborated === false
  );

  let result;
  let reason;
  if (!settled.succeeded) {
    result = "NOT_CONFIRMED";
    reason = `reverted: ${settled.error}`;
  } else if (effects.length === 0 && !viewCommitted) {
    result = "NOT_CONFIRMED";
    reason = "effects identical (no protected effect committed)";
  } else if (violations.length === 0) {
    result = "NOT_CONFIRMED";
    reason = "policy-permitted";
  } else if (uncorroborated.length > 0) {
    // XR-01: an emitted Transfer not backed by a state change cannot carry E4.
    result = "UNKNOWN";
    reason = `EFFECT_NOT_STATE_CORROBORATED: ${uncorroborated
      .map((e) => `${e.contract_role || e.contract}:${e.state_corroboration.reason}`)
      .join("; ")}`;
  } else if (!verifierPath.established) {
    // XR-02: the unchanged verifier was not shown to accept on the mutated path.
    result = "UNKNOWN";
    reason = `VERIFIER_PATH_NOT_ESTABLISHED: ${verifierPath.reason}`;
  } else {
    result = "E4-CONFIRMED";
    reason = "mutated tx succeeded; unchanged verifier accepted on the mutated path; a state-corroborated protected effect violates the policy";
  }

  return jsonSafe({
    ...trial,
    result,
    reason,
    verifier_accepted_preflight: va.accepted,
    verifier_checks_preflight: va.results,
    verifier_on_mutated_path: verifierPath,
    tx_succeeded: settled.succeeded,
    tx_hash: settled.hash,
    tx_error: settled.error,
    mutated_sender: from.address,
    alias: aliasNote,
    prelude: prelude ? { succeeded: prelude.succeeded, hash: prelude.hash } : null,
    protected_effects: effects,
    policy_violations: violations,
    obligations,
    view_effects: {
      deltas: Object.fromEntries(Object.entries(viewDeltas).map(([k, v]) => [k, v.toString()])),
      honest_deltas: Object.fromEntries(
        Object.entries(env.honestViewDeltas || {}).map(([k, v]) => [k, v.toString()])
      ),
      protected_committed: viewCommitted,
    },
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

// ---- view-based effects (S4d / AZ1) ----------------------------------------
//
// Some protected effects and obligations are state-accounting changes with no
// Transfer event (e.g. an L2 credit counter, or settled backing). The manifest
// declares `scenario.state_views: [{name, contract, function, args?}]`; the
// driver reads each as a uint before and after the mutated tx (and in the honest
// reference) and works from the signed deltas. These are read-only `view` calls
// on owned local deployments, so a view effect is state by construction (it
// needs no separate XR-01 corroboration).

async function readStateViews(deployments, scenario, resolver) {
  const out = {};
  for (const v of scenario.state_views || []) {
    const dep = deployments[v.contract];
    if (!dep) continue;
    try {
      const args = (v.args || []).map((a) => resolver.resolve(a));
      const raw = await dep.contract[v.function](...args);
      out[v.name] = BigInt(raw);
    } catch (_) {
      /* view missing or reverted: left unset (treated as absent) */
    }
  }
  return out;
}

function diffViews(before, after) {
  const deltas = {};
  for (const name of new Set([...Object.keys(before), ...Object.keys(after)])) {
    const b = before[name] ?? 0n;
    const a = after[name] ?? 0n;
    deltas[name] = a - b; // bigint
  }
  return deltas;
}

// Does any declared protected view effect commit (its delta reaches min_delta)?
function protectedViewCommitted(policy, viewDeltas) {
  for (const pe of policy.protected_view_effects || []) {
    const d = viewDeltas[pe.view] ?? 0n;
    if (d >= BigInt(pe.min_delta ?? "1")) return true;
  }
  return false;
}

// Undischarged view obligations (S4d). A `view_obligation` says the obligation
// view's delta must equal the credited protected view's delta (e.g. settled
// backing must equal the L2 credit granted). It is faulted only when the honest
// path discharged it (honest backing delta == honest credit delta, credit > 0)
// and this mutated tx granted the credit but moved the backing by less.
function evaluateViewObligations(policy, viewDeltas, honestViewDeltas) {
  const violations = [];
  const honest = honestViewDeltas || {};
  for (const obl of policy.view_obligations || []) {
    const creditDelta = viewDeltas[obl.must_equal_credit_of] ?? 0n;
    const backingDelta = viewDeltas[obl.view] ?? 0n;
    const honestCredit = honest[obl.must_equal_credit_of] ?? 0n;
    const honestBacking = honest[obl.view] ?? 0n;
    const honestDischarged = honestCredit > 0n && honestBacking === honestCredit;
    if (honestDischarged && creditDelta > 0n && backingDelta < creditDelta) {
      violations.push({
        rule: obl.id,
        type: "undischarged_view_obligation",
        obligation: obl.id,
        description: obl.description || null,
        credited_view: obl.must_equal_credit_of,
        credited_delta: creditDelta.toString(),
        obligation_view: obl.view,
        obligation_delta: backingDelta.toString(),
        shortfall: (creditDelta - backingDelta).toString(),
      });
    }
  }
  return violations;
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
  const honestViewBefore = await readStateViews(honestDeploy.deployments, scenario, honestResolver);
  const honestSettled = await sendTx(
    honestDeploy.deployments[scenario.honest_tx.target],
    scenario.honest_tx.function,
    honestArgs,
    honestResolver.signer(scenario.honest_tx.from),
    scenario.honest_tx.value ? honestResolver.resolve(scenario.honest_tx.value) : null
  );
  const honestViewAfter = await readStateViews(honestDeploy.deployments, scenario, honestResolver);
  env.honestViewDeltas = diffViews(honestViewBefore, honestViewAfter);
  const honestEffects = honestSettled.succeeded
    ? extractEffects(honestSettled.receipt, honestDeploy.deploymentsByAddr)
    : [];
  // Required obligations the honest path discharges, with multiplicity (S4c +
  // XR-07). A mutated trial can only be faulted for omitting an obligation the
  // honest path itself commits, and only down to the honest occurrence count.
  const honestObligations = {};
  for (const obl of spec.policy.required_obligations || []) {
    honestObligations[obl.id] = obligationCount(honestEffects, obl.match || {}, honestResolver);
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
    view_deltas: Object.fromEntries(
      Object.entries(env.honestViewDeltas || {}).map(([k, v]) => [k, v.toString()])
    ),
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

// Run only when executed directly; `require()` (e.g. the unit tests) just loads
// the exported pure helpers without starting a trial run.
if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 2;
  });
}

module.exports = {
  FIELD_R,
  extractEffects,
  evaluatePolicy,
  matchesObligation,
  obligationCount,
  flattenCalls,
  verifierOnMutatedPath,
  diffViews,
  protectedViewCommitted,
  evaluateViewObligations,
};
