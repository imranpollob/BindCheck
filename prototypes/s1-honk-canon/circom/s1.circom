pragma circom 2.1.0;
// Owned synthetic S1 circuit: one public input n with secret * secret == n.
template S1() {
    signal input secret;
    signal input n;
    n === secret * secret;
}
component main {public [n]} = S1();
