struct Pair {
    values: [Field; 2],
}

struct Envelope {
    tag: Field,
    pair: Pair,
}

fn main(envelope: pub Envelope, tail: pub [Field; 2], secret: Field) {
    assert(envelope.tag + envelope.pair.values[0] + envelope.pair.values[1] + tail[0] + secret == tail[1]);
}
