fn main(amount: pub Field, max_fee: pub Field) {
    assert(!amount.lt(max_fee), "max_fee higher than amount");
}
