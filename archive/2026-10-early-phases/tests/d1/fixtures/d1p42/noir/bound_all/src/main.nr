fn main(values: pub [Field; 4], active_count: pub u32, expected: [Field; 4]) {
    assert(active_count <= 4);
    for i in 0..4 {
        assert(values[i] == expected[i]);
    }
}
