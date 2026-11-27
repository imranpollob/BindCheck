fn main(left: pub Field, right: pub Field, expected: pub Field) {
    let values = [left, right];
    assert(values[1] == expected);
}
