fn main(value: pub Field, index: pub u32) {
    let mut values = [0, 0];
    values[index] = value;
    assert(index < 2);
}
