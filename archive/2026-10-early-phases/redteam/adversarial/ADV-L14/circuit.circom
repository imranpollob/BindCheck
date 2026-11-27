pragma circom 2.1.6;

template App() {
    signal input secret;
    signal input chainId;
    signal output nullifier;
    nullifier <== secret + chainId;
}

component main {public [chainId]} = App();
