Generated locally with snarkjs 0.7.6 and Circom 2.2.3 from `m.circom`
(powers-of-tau 2^4, one throwaway contribution each phase).

- `snarkjs_0000_default_key.sol`: exported from the uncontributed `_0000.zkey`;
  snarkjs sets gamma to the G2 generator and delta equals gamma before any
  phase-2 contribution (gamma = delta, forgeable).
- `snarkjs_0001_contributed_key.sol`: exported after one phase-2 contribution
  (gamma != delta).
