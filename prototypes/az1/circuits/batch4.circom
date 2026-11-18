pragma circom 2.1.0;

// AZ1 synthetic detector fixture. Not derived from any deployed circuit.
// A fixed-size batch of N rows. The proof commits to ALL N rows and to the
// total credit over ALL N rows. It carries no "number of real rows".

include "circomlib/circuits/poseidon.circom";
include "circomlib/circuits/bitify.circom";

template Batch(N) {
    signal input kind[N];    // 0 = no-op, 1 = deposit
    signal input owner[N];   // account identifier (an address as an integer)
    signal input amount[N];  // test-token amount

    signal output commitment;   // Poseidon over every row
    signal output creditTotal;  // sum of amounts over every row

    component rowHash[N];
    component range[N];
    component top = Poseidon(N);
    signal partial[N + 1];
    partial[0] <== 0;

    for (var i = 0; i < N; i++) {
        kind[i] * (kind[i] - 1) === 0;
        // a no-op row carries no owner and no amount
        (1 - kind[i]) * amount[i] === 0;
        (1 - kind[i]) * owner[i] === 0;

        range[i] = Num2Bits(64);
        range[i].in <== amount[i];

        rowHash[i] = Poseidon(3);
        rowHash[i].inputs[0] <== kind[i];
        rowHash[i].inputs[1] <== owner[i];
        rowHash[i].inputs[2] <== amount[i];
        top.inputs[i] <== rowHash[i].out;

        partial[i + 1] <== partial[i] + amount[i];
    }

    commitment <== top.out;
    creditTotal <== partial[N];
}

component main = Batch(4);
