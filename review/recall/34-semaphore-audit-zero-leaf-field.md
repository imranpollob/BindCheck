# Recall card 34 — semaphore-audit-zero-leaf-field

`semaphore-audit-zero-leaf-field`

| Field | Value |
|---|---|
| Repository | privacy-scaling-explorations/zk-kit |
| DSL (ledger) | Circom/Solidity or generated Groth16 verifier |
| Ledger pattern / impact | contract accepts tree value outside SNARK scalar field / proof-to-execution mismatch |
| Class v1 → v2 | `integration` → `integration` |
| Vulnerable → fixed | [cc21bb125f](https://github.com/privacy-scaling-explorations/zk-kit/tree/cc21bb125fb594772e7e46111fdba05845a06355) → MISSING (not-publicly-pinned) |
| Exposure | not exposed by C2; RELATED DEV repos in same org: privacy-scaling-explorations/maci |
| L4 proposal | **ADVISORY: DROP-CANDIDATE (liveness, not authorization)** |

## 1. Source report (verbatim)

```text
[M1] Missing ZK snark scalar field check on 0 leaf in dependency
Location
https://github.com/privacy-scaling-explorations/zk-kit/blob/cc21bb125fb594772e7e46111fdba058
45a06355/packages/incremental-merkle-tree.sol/contracts/IncrementalBinaryTree.sol#L29
Description
During initialization of the IncrementalBinaryTree.sol, the user can enter any value for the
uint256 zero field. This becomes an issue if the user uses a value greater than the
SNARK_SCALAR_FIELD. A zero leaf can be inside an array of proofSiblings when proving
existence of a leaf which may cause an issue when the IncrementalBinaryTree.verify function is
called during the IncrementalBinaryTree.remove function. The verify function requires that all
proofSiblings are less than the SNARK_SCALAR_FIELD. So, if the 'zero' leaf is greater than the
SNARK_SCALAR_FIELD, this verify function will unintentionally fail.
Suggested Solution
Add a require(zero < SNARK_SCALAR_FIELD, "...") statement in the
IncrementalBinaryTree.init() function.
```

<sub>Source: Semaphore 2.0.0 audit PDF, pdftotext -layout lines 187-204 of `results/raw/groundtruth/sources/semaphore-2.0.0-audit.txt` (sha256 975d9b029e18…)</sub>

## 2. Vulnerable vs fixed code

> **Candidate fixed commit (not a ledger pin):** Fix Log names zk-kit issue #23 (closed 2022-03-09T17:10:28Z). Commit 6ea92745 ('fix: add checks to ensure zeroes are valid zk values', 2022-03-09T17:03:26Z) adds exactly the recommended require. CANDIDATE only.

#### `packages/incremental-merkle-tree.sol/contracts/IncrementalBinaryTree.sol`

<table><tr><th>Vulnerable @ <code>cc21bb125f</code>, lines 25–40</th><th>CANDIDATE fixed @ <code>6ea9274542</code>, lines 25–41</th></tr>
<tr><td valign="top"><pre>  25    /// @dev Initializes a tree.
  26    /// @param self: Tree data.
  27    /// @param depth: Depth of the tree.
  28    /// @param zero: Zero value to be used.
  29    function init(
  30      IncrementalTreeData storage self,
  31      uint8 depth,
  32      uint256 zero
  33    ) public {
  34      require(depth &gt; 0 &amp;&amp; depth &lt;= MAX_DEPTH, &quot;IncrementalBinaryTree: tree depth must be between 1 and 32&quot;);
  35  
  36      self.depth = depth;
  37  
  38      for (uint8 i = 0; i &lt; depth; i++) {
  39        self.zeroes[i] = zero;
  40        zero = PoseidonT3.poseidon([zero, zero]);</pre></td><td valign="top"><pre>  25    /// @dev Initializes a tree.
  26    /// @param self: Tree data.
  27    /// @param depth: Depth of the tree.
  28    /// @param zero: Zero value to be used.
  29    function init(
  30      IncrementalTreeData storage self,
  31      uint8 depth,
  32      uint256 zero
  33    ) public {
  34      require(zero &lt; SNARK_SCALAR_FIELD, &quot;IncrementalBinaryTree: leaf must be &lt; SNARK_SCALAR_FIELD&quot;);
  35      require(depth &gt; 0 &amp;&amp; depth &lt;= MAX_DEPTH, &quot;IncrementalBinaryTree: tree depth must be between 1 and 32&quot;);
  36  
  37      self.depth = depth;
  38  
  39      for (uint8 i = 0; i &lt; depth; i++) {
  40        self.zeroes[i] = zero;
  41        zero = PoseidonT3.poseidon([zero, zero]);</pre></td></tr></table>


## 3. L4 analysis (proposal, not a decision)

- **Boundary value:** yes - zero leaf can appear in proofSiblings passed to verify
- **Consumer consequence:** denial of service only - 'verify function will unintentionally fail' (completeness, not an unauthorised effect)
- **Fix locus:** consumer library (require(zero < SNARK_SCALAR_FIELD))
- **P1–P5 mappable:** no - no P1-P5 predicate covers a liveness failure
- **Research-contract scope:** contract s5.4 lists unconditional liveness as out of scope; the effect is a DoS
- **Relational class:** CONSUMER-ONLY — library init range check
- **Proposed expected pattern:** `NONE`
- **Proposed location regex** (matches `path:line` from `eval/common.py:pattern_locations`): `^packages/incremental-merkle-tree\.sol/contracts/IncrementalBinaryTree\.sol(:\d+)?$`
- **Location basis:** init at vulnerable IncrementalBinaryTree.sol:29 (audit link #L29)
- **Concerns:**
  - Fixed pin MISSING in ledger; candidate 6ea92745423ad3e4104f16a2cec7d4d6c69ade72.

## 4. Reviewer decision

| Field | Fill in |
|---|---|
| Decision | ☐ ACCEPT  ☐ EDIT  ☐ DROP |
| Strict scope (keep / demote) | |
| expected_pattern (P1–P5 or NONE) | |
| expected_location_regex | |
| Accept candidate commit? (if shown) | ☐ yes ☐ no ☐ n/a |
| Reviewer | |
| Date | |
| Notes | |
