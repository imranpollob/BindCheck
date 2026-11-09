pragma circom 2.1.6;

template App() {
    signal input recipient;
    signal input amount;
    signal output commitment;
    commitment <== recipient * 1000003 + amount;
}

component main = App();
