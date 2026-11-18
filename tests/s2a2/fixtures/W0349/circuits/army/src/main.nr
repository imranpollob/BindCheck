use dep::std;

//
//  Helper function that validates the total army population is equal to 1000
//
//  Input:
//      army { [Field; 3] } - army[0] --> infantry population
//                          - army[1] --> artillery population 
//                          - army[2] --> tanks population 
//
fn validate_army(army: [Field; 3]) -> Field {
    let total_population = army[0] + army[1] + army[2];
    assert(total_population == 1000 as Field, "Army population should be equal to 1000!");

    let computed_hash = std::hash::pedersen_hash(army);
    computed_hash
}

//
//  Circuit that validates army selection for a Game
//
//  Input:
//      army_hash { pub Field } - Pedersen hash computed outside of circuit that represents army state
//      army { [Field; 3] } - army[0] --> infantry population
//                          - army[1] --> artillery population 
//                          - army[2] --> tanks population 
//
fn main(army_hash: pub Field, army: [Field; 3]) {
    let computed_hash = validate_army(army);
    assert(army_hash == computed_hash, "Army hash integrity check failed!");
}

/// ARMY CIRCUIT TESTS ///

#[test]
fn test_valid_army() {
    let army = [200, 300, 500];
    let hash = std::hash::pedersen_hash(army);

    main(hash, army);
}

#[test(should_fail_with = "Army population should be equal to 1000!")]
fn test_invalid_army_less() {
    // army_population = 900 < 1000 --> should fail
    let army = [300, 400, 200];
    let hash = std::hash::pedersen_hash(army);

    main(hash, army);
}

#[test(should_fail_with = "Army population should be equal to 1000!")]
fn test_invalid_army_more() {
    // army_population = 1200 > 1000 --> should fail
    let army = [300, 400, 500];
    let hash = std::hash::pedersen_hash(army);

    main(hash, army);
}

#[test(should_fail_with = "Army hash integrity check failed!")]
fn test_invalid_army_hash() {
    let army = [300, 400, 300];
    // tamper with army hash preimage
    let hash = std::hash::pedersen_hash([200, 500, 300]);

    main(hash, army);
}
