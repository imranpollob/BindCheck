pragma circom 2.1.6;

template App() {
    signal input recipient;
    signal input amount;
    signal input nullifier;
    signal input activeLength;
    signal input items[4];
    signal input maskA[4];
    signal input maskB[4];
    signal terms[4];
    signal output digest;
    var total = 0;
    for (var i = 0; i < 4; i++) {
        maskA[i] * (maskA[i] - 1) === 0;
        maskB[i] * (maskB[i] - 1) === 0;
        terms[i] <== items[i] * (maskA[i] + maskB[i]);
        total += terms[i];
    }
    digest <== recipient + amount + nullifier + activeLength + total;
}

component main {public [recipient, amount, nullifier, activeLength]} = App();
