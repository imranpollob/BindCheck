pragma circom 2.1.6;

template App() {
    signal input secret;
    signal input contractAddress;
    signal output nullifier;
    nullifier <== secret + contractAddress;
}

component main {public [contractAddress]} = App();
