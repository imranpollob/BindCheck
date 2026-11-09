pragma circom 2.1.6;

template App() {
    signal input recipient;
    signal input amount;
    signal input nullifier;
    signal input activeLength;
    signal input items[4];
    signal input enabled[4];
    signal terms[4];
    signal output digest;
    var total = 0;
    var enabledTotal = 0;
    for (var i = 0; i < 4; i++) {
        enabled[i] * (enabled[i] - 1) === 0;
        terms[i] <== items[i] * enabled[i];
        total += terms[i];
        enabledTotal += enabled[i];
    }
    enabledTotal === activeLength;
    digest <== recipient + amount + nullifier + total;
}

component main {public [recipient, amount, nullifier, activeLength]} = App();
