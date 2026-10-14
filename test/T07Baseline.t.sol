// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {T01Fixture} from "./T01Fixture.sol";
import {BaselineProperty} from "./BaselineProperty.sol";
import {Observation} from "./Observation.sol";
import {BackedBatchConsumer} from "../contracts/BackedBatchConsumer.sol";
import {ResearchMutantBackedBatchConsumer} from "../contracts/research/MutantBackedBatchConsumer.sol";
import {RepairedPrefixBatchConsumer} from "../contracts/research/RepairedPrefixBatchConsumer.sol";
import {IGroth16Verifier} from "../contracts/BatchConsumer.sol";
import {Groth16Verifier} from "../contracts/generated/Groth16Verifier.sol";

/// T07: systematic finite enumeration over the two existing valid proof fixtures.
///   fixtures : original [100,250,0,40]/[1,1,0,1] (3 active rows), padded [100,250,0,0]/[1,1,0,0] (2 active rows)
///   funding  : every subset of ACTIVE rows (inactive row 2 is never funded)
///   limits   : 0..4 for the mutant and repaired consumers; the correct consumer has no limit (once per subset)
/// Every case uses fresh deployments of the consumer, the real generated verifier and the real proofs.
/// Per case: execute, evaluate the direct baseline property, export a record for the trace checker, and write the
/// baseline result to a SEPARATE directory (results/raw/T07/baseline). The checker never sees the baseline files.
/// Finite enumeration only: no claim about other amounts, witnesses, circuits or transaction sequences.
contract T07BaselineTest is T01Fixture, BaselineProperty, Observation {
    uint256 constant PADDED_NEW_COMMITMENT = 13087091886095216173338600835649502128422847627890228330606202401392478644873;

    enum Kind { Correct, Mutant, Repaired }

    struct Cfg {
        uint256 n;
        Kind kind;
        bool padded;
        uint256 fundMask;
        uint256 limit;
    }

    struct Tally {
        uint256 cases;
        uint256 successes;
        uint256 reverts;
        uint256 violations;
        uint256 unchangedReverts;
        uint256 holds;
    }

    uint256[2] qA;
    uint256[2][2] qB;
    uint256[2] qC;
    uint256[10] qpub;

    function setUp() public {
        _loadFixture();
        string memory j = vm.readFile("build/T05/calldata.json");
        uint256[] memory a = vm.parseJsonUintArray(j, "$[0]");
        uint256[] memory b0 = vm.parseJsonUintArray(j, "$[1][0]");
        uint256[] memory b1 = vm.parseJsonUintArray(j, "$[1][1]");
        uint256[] memory c = vm.parseJsonUintArray(j, "$[2]");
        uint256[] memory p = vm.parseJsonUintArray(j, "$[3]");
        qA = [a[0], a[1]];
        qB = [[b0[0], b0[1]], [b1[0], b1[1]]];
        qC = [c[0], c[1]];
        for (uint256 i = 0; i < 10; i++) qpub[i] = p[i];
        uint256[10] memory expectedP = [uint256(100), 250, 0, 0, 1, 1, 0, 0, OLD_COMMITMENT, PADDED_NEW_COMMITMENT];
        for (uint256 i = 0; i < 10; i++) assertEq(qpub[i], expectedP[i], "padded fixture differs");
        verifier = new Groth16Verifier();
        assertTrue(verifier.verifyProof(pA, pB, pC, pub), "original proof verifies");
        assertTrue(verifier.verifyProof(qA, qB, qC, qpub), "padded proof verifies");
        vm.createDir("results/raw/T07/records", true);
        vm.createDir("results/raw/T07/baseline", true);
    }

    // ---------- configuration helpers ----------
    function _proof(bool padded) internal view returns (Proof memory) {
        return padded ? Proof(qA, qB, qC, qpub) : Proof(pA, pB, pC, pub);
    }

    function _activeMask(bool padded) internal view returns (uint256 m) {
        uint256[10] memory p = _proof(padded).p;
        for (uint256 r = 0; r < 4; r++) if (p[4 + r] == 1) m |= 1 << r;
    }

    function _deploy(Kind k) internal returns (address) {
        IGroth16Verifier v = IGroth16Verifier(address(verifier));
        if (k == Kind.Correct) return address(new BackedBatchConsumer(v, OLD_COMMITMENT));
        if (k == Kind.Mutant) return address(new ResearchMutantBackedBatchConsumer(v, OLD_COMMITMENT));
        return address(new RepairedPrefixBatchConsumer(v, OLD_COMMITMENT));
    }

    function _fund(address c, Proof memory pr, uint256 row) internal {
        (bool ok,) = c.call{value: pr.p[row]}(abi.encodeWithSignature("fund(uint256[10],uint256)", pr.p, row));
        require(ok, "fund failed");
    }

    function _submitData(Kind k, Proof memory pr, uint256 limit) internal pure returns (bytes memory) {
        if (k == Kind.Correct) return abi.encodeCall(BackedBatchConsumer.submit, (pr.a, pr.b, pr.c, pr.p));
        if (k == Kind.Mutant) return abi.encodeCall(ResearchMutantBackedBatchConsumer.submit, (pr.a, pr.b, pr.c, pr.p, limit));
        return abi.encodeCall(RepairedPrefixBatchConsumer.submit, (pr.a, pr.b, pr.c, pr.p, limit));
    }

    function _kindName(Kind k) internal pure returns (string memory) {
        return k == Kind.Correct ? "correct" : (k == Kind.Mutant ? "mutant" : "repaired");
    }

    function _caseId(uint256 n) internal pure returns (string memory) {
        string memory s = vm.toString(n);
        return string.concat("c-", n < 10 ? "00" : (n < 100 ? "0" : ""), s);
    }

    function _rowsJson(uint256 mask) internal pure returns (string memory out) {
        out = "[";
        bool first = true;
        for (uint256 r = 0; r < 4; r++) {
            if (mask & (1 << r) == 0) continue;
            out = string.concat(out, first ? "" : ",", vm.toString(r));
            first = false;
        }
        out = string.concat(out, "]");
    }

    function _violationsJson(Eval memory e, uint256[10] memory p) internal pure returns (string memory out) {
        out = "[";
        bool first = true;
        for (uint256 r = 0; r < 4; r++) {
            if (e.violationMask & (1 << r) == 0) continue;
            out = string.concat(
                out, first ? "" : ",", '{"row":', vm.toString(r), ',"amount":"', vm.toString(p[r]),
                '","fundedButUnconsumed":', (e.fundedButUnconsumedMask & (1 << r) != 0) ? "true" : "false", "}"
            );
            first = false;
        }
        out = string.concat(out, "]");
    }

    function _writeBaseline(Cfg memory cfg, Eval memory e, uint256[10] memory p) internal {
        string memory head = string.concat(
            '{"caseId":"', _caseId(cfg.n), '","consumer":"', _kindName(cfg.kind), '","fixture":"',
            cfg.padded ? "padded" : "original", '","fundedRows":', _rowsJson(cfg.fundMask), ',"limit":',
            cfg.kind == Kind.Correct ? "null" : string.concat('"', vm.toString(cfg.limit), '"'), ","
        );
        string memory body = string.concat(
            '"status":"', e.success ? "success" : "reverted", '","baseline":{"holds":', e.holds ? "true" : "false",
            ',"commitmentOk":', e.commitmentOk ? "true" : "false", ',"accountingOk":', e.accountingOk ? "true" : "false",
            ',"stateUnchanged":', e.stateUnchanged ? "true" : "false", ',"violations":', _violationsJson(e, p),
            ',"missingAmount":"', vm.toString(e.missingAmount), '"}}'
        );
        vm.writeFile(string.concat("results/raw/T07/baseline/", _caseId(cfg.n), ".json"), string.concat(head, body));
    }

    // ---------- one case ----------
    function _runCase(Cfg memory cfg, Tally memory t) internal {
        Proof memory pr = _proof(cfg.padded);
        address c = _deploy(cfg.kind);                       // fresh consumer
        bytes32 id = keccak256(abi.encode(pr.p));
        assertEq(uint256(vm.load(c, bytes32(uint256(0)))), OLD_COMMITMENT, "fresh consumer");
        for (uint256 r = 0; r < 4; r++) if (cfg.fundMask & (1 << r) != 0) _fund(c, pr, r);

        RawSnap memory pre = _rawSnap(c, id);
        bool ok = _execute(_caseId(cfg.n), c, pr, _submitData(cfg.kind, pr, cfg.limit));
        RawSnap memory post = _rawSnap(c, id);

        Eval memory e = _evaluate(ok, pr.p, pre, post);
        _writeBaseline(cfg, e, pr.p);

        t.cases++;
        if (ok) {
            t.successes++;
            if (e.violationMask != 0 || !e.commitmentOk || !e.accountingOk) t.violations++;
        } else {
            t.reverts++;
            if (e.stateUnchanged) t.unchangedReverts++;
        }
        if (e.holds) t.holds++;
    }

    function _enumerate(Kind k, bool padded, uint256 base, bool assertProperty) internal returns (Tally memory t) {
        uint256 active = _activeMask(padded);
        uint256 n = base;
        uint256 limits = k == Kind.Correct ? 1 : 5;
        for (uint256 mask = 0; mask < 16; mask++) {
            if (mask & ~active != 0) continue; // never fund an inactive row
            for (uint256 limit = 0; limit < limits; limit++) {
                Cfg memory cfg = Cfg(n, k, padded, mask, limit);
                // The assertion form of the property is exercised in _runCase's caller below.
                _runCase(cfg, t);
                n++;
            }
        }
        if (assertProperty) {
            // conventional passing property test: re-evaluate from the baseline results the run just produced
            assertEq(t.holds, t.cases, "direct coverage property failed on an enumerated case");
        }
    }

    // ---------- enumeration tests (case numbering: ids are opaque and contiguous across all six) ----------
    // correct: original 8 subsets (c-001..008), padded 4 subsets (c-009..012)
    // mutant : original 8 x 5 (c-013..052), padded 4 x 5 (c-053..072)
    // repaired: original 8 x 5 (c-073..112), padded 4 x 5 (c-113..132)
    function test_enumerate_correct_original() public {
        Tally memory t = _enumerate(Kind.Correct, false, 1, true);
        assertEq(t.cases, 8);
    }

    function test_enumerate_correct_padded() public {
        Tally memory t = _enumerate(Kind.Correct, true, 9, true);
        assertEq(t.cases, 4);
    }

    function test_enumerate_mutant_original() public {
        Tally memory t = _enumerate(Kind.Mutant, false, 13, false);
        assertEq(t.cases, 40);
        assertGt(t.violations, 0, "enumeration should expose violations in the mutant");
    }

    function test_enumerate_mutant_padded() public {
        Tally memory t = _enumerate(Kind.Mutant, true, 53, false);
        assertEq(t.cases, 20);
        assertGt(t.violations, 0, "enumeration should expose violations in the mutant");
    }

    function test_enumerate_repaired_original() public {
        Tally memory t = _enumerate(Kind.Repaired, false, 73, true);
        assertEq(t.cases, 40);
    }

    function test_enumerate_repaired_padded() public {
        Tally memory t = _enumerate(Kind.Repaired, true, 113, true);
        assertEq(t.cases, 20);
    }

    // ---------- the assertion form of the property on a known case (documents the standalone assertion) ----------
    function test_standaloneAssertion_holdsOnHonestSettlement_andFailsOnKnownCoverageGap() public {
        // honest: correct consumer, all active rows funded
        Proof memory pr = _proof(false);
        address c = _deploy(Kind.Correct);
        for (uint256 r = 0; r < 4; r++) if (pr.p[4 + r] == 1) _fund(c, pr, r);
        bytes32 id = keccak256(abi.encode(pr.p));
        RawSnap memory pre = _rawSnap(c, id);
        (bool ok,) = c.call(_submitData(Kind.Correct, pr, 0));
        assertTrue(ok);
        assertCoverageProperty(_evaluate(ok, pr.p, pre, _rawSnap(c, id)), "honest");

        // known gap: mutant, row 3 funded but limit 3 -> the assertion must reject (try/catch on an external wrapper)
        address m = _deploy(Kind.Mutant);
        for (uint256 r = 0; r < 4; r++) if (pr.p[4 + r] == 1) _fund(m, pr, r);
        RawSnap memory mpre = _rawSnap(m, id);
        (bool mok,) = m.call(_submitData(Kind.Mutant, pr, 3));
        assertTrue(mok);
        Eval memory me = _evaluate(mok, pr.p, mpre, _rawSnap(m, id));
        assertFalse(me.holds);
        assertEq(me.violationMask, 1 << 3);
        assertEq(me.missingAmount, 40);
        assertEq(me.fundedButUnconsumedMask, 1 << 3);
        try this.externalAssert(me) { revert("assertion should have rejected the coverage gap"); } catch {}
    }

    function externalAssert(Eval memory e) external pure {
        assertCoverageProperty(e, "mutant limit 3");
    }

    // ---------- proof-acceptance inference depends on the consumer enforcing the verifier result ----------
    function test_eachEvaluatedConsumerEnforcesTheVerifierResult() public {
        Proof memory pr = _proof(false);
        bytes memory invalidProof = abi.encodeWithSignature("InvalidProof()");
        for (uint256 k = 0; k < 3; k++) {
            Kind kind = Kind(k);
            address c = _deploy(kind);
            for (uint256 r = 0; r < 4; r++) if (pr.p[4 + r] == 1) _fund(c, pr, r);
            // altered public amount with the original proof; old commitment still matches the stored one
            Proof memory bad = _proof(false);
            bad.p[0] += 1;
            assertFalse(verifier.verifyProof(bad.a, bad.b, bad.c, bad.p));
            bytes32 id = keccak256(abi.encode(pr.p));
            RawSnap memory pre = _rawSnap(c, id);
            (bool ok, bytes memory ret) = c.call(_submitData(kind, bad, 4));
            assertFalse(ok, string.concat(_kindName(kind), ": accepted a proof the verifier rejects"));
            assertEq(keccak256(ret), keccak256(invalidProof), string.concat(_kindName(kind), ": revert is not InvalidProof"));
            assertTrue(_same(pre, _rawSnap(c, id)));
        }
    }
}
