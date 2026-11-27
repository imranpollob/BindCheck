pragma circom 2.1.0;

// BindCheck T01 fixture: one-balance, four-slot batch of deposit credits.
//
// Statement (public: amount[4], active[4], oldCommitment, newCommitment):
//   there exist oldBalance, newBalance (private) such that
//     - every active[i] is Boolean
//     - every amount[i] is an unsigned 32-bit integer
//     - oldBalance and newBalance are unsigned 64-bit integers
//     - active[i] == 0  =>  amount[i] == 0
//     - newBalance == oldBalance + sum_i active[i] * amount[i]
//     - oldCommitment == Poseidon([oldBalance]), newCommitment == Poseidon([newBalance])
//
// The commitments are UNSALTED and the balances low-entropy: this is an
// engineering fixture, not a confidentiality claim and not a payment protocol.
// There are no deposit identities, backing, domains or nullifiers here.
//
// Field-wrap note: oldBalance < 2^64 and sum <= 4*(2^32-1) < 2^34, so the
// right-hand side is < 2^65 << p (BN254 scalar field, ~2^253.6). The field
// equality therefore coincides with integer equality, and newBalance < 2^64
// rejects integer overflow past 64 bits.

include "circomlib/circuits/bitify.circom";
include "circomlib/circuits/poseidon.circom";

template BatchDeposit(N) {
    // Public inputs. Declaration order here fixes the public-signal order.
    signal input amount[N];
    signal input active[N];
    signal input oldCommitment;
    signal input newCommitment;

    // Private inputs.
    signal input oldBalance;
    signal input newBalance;

    // Activation flags are Boolean: a * (a - 1) == 0.
    for (var i = 0; i < N; i++) {
        active[i] * (active[i] - 1) === 0;
    }

    // Amounts are unsigned 32-bit; balances are unsigned 64-bit.
    component amountBits[N];
    for (var i = 0; i < N; i++) {
        amountBits[i] = Num2Bits(32);
        amountBits[i].in <== amount[i];
    }
    component oldBits = Num2Bits(64);
    oldBits.in <== oldBalance;
    component newBits = Num2Bits(64);
    newBits.in <== newBalance;

    // Inactive rows carry zero amount: (1 - active[i]) * amount[i] == 0.
    for (var i = 0; i < N; i++) {
        (1 - active[i]) * amount[i] === 0;
    }

    // newBalance == oldBalance + sum(active[i] * amount[i]).
    signal term[N];
    var sum = 0;
    for (var i = 0; i < N; i++) {
        term[i] <== active[i] * amount[i];
        sum += term[i];
    }
    newBalance === oldBalance + sum;

    // Commitments bind to the corresponding balances.
    component oldHash = Poseidon(1);
    oldHash.inputs[0] <== oldBalance;
    oldHash.out === oldCommitment;

    component newHash = Poseidon(1);
    newHash.inputs[0] <== newBalance;
    newHash.out === newCommitment;
}

component main {public [amount, active, oldCommitment, newCommitment]} = BatchDeposit(4);
