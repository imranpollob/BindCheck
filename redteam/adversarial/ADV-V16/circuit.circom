pragma circom 2.1.6;

template App() {
    signal input recipient;
    signal input amount;
    signal output commitment;
    commitment <== amount * 1000003 + recipient;
}

component main = App();
