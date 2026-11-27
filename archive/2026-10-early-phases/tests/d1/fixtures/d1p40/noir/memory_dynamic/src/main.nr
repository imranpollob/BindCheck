fn main(left: pub Field, right: pub Field, index: pub u32, expected: pub Field) {
    let values = [left, right];
    assert(values[index] == expected);
}
