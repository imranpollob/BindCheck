pragma circom 2.1.6;

template App() {
    signal input secret;
    signal input contractAddress;
    signal output nullifier;
    nullifier <== secret;
}

component main {public [contractAddress]} = App();
