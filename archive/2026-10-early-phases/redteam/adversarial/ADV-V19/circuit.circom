pragma circom 2.1.6;

template App() {
    signal input recipient;
    signal input amount;
    signal input nullifier;
    signal input activeLength;
    signal output digest;
    signal output publicAlias;
    publicAlias <== recipient;
    digest <== recipient + amount + nullifier + activeLength;
}

component main {public [recipient, amount, nullifier, activeLength]} = App();
