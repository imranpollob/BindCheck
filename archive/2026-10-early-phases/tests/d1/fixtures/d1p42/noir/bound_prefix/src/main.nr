fn main(values: pub [Field; 4], active_count: pub u32, expected: [Field; 4]) {
    for i in 0..4 {
        if i < active_count {
            assert(values[i] == expected[i]);
        }
    }
}
