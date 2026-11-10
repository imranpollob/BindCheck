pragma circom 2.1.6;

template App() {
    signal input recipient;
    signal input amount;
    signal output commitment;
    commitment <== recipient;
}

component main = App();
