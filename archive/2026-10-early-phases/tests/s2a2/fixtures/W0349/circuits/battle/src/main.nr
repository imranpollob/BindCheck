use dep::std;

// Helper function that returns 1 if unit1 > unit2 and 0 otherwise
fn battle_clash(unit1: u10, unit2: u10) -> u4 {
    if unit1 >= unit2 { 1 } else { 0 }
}

//
//  Helper function that proves the output of a battle between two armies
//  ==> Depending on each rule of army attribute(infantry, artillery, tanks) battle each player will score points.
//  ==> A battle point for a win is 1 and 0 otherwise.
//  ==> Returns 1 if battepoints >=2 and 0 otherwise.
//  !NOTE: The rules defined below are subjected to change in the future.
//
//  Inputs:
//      my_army { [Field; 3] } - army[0] --> infantry population
//                             - army[1] --> artillery population 
//                             - army[2] --> tanks population
//  
//      adversary_army { [Field; 3] } - army[0] --> infantry population
//                                    - army[1] --> artillery population 
//                                    - army[2] --> tanks population 
//
fn attack(my_army: [Field; 3], adversary_army: [Field; 3]) -> Field {
    let mut battle_points = 0 as u2;

    // Rule1: Infantry beats Artillery
    let my_infantry = (my_army[0]) as u10;
    let adversary_artillery = adversary_army[1] as u10;
    let battle1_output = battle_clash(my_infantry, adversary_artillery);
    battle_points += battle1_output as u2;

    // Rule2: Artillery beats Tanks
    let my_artillery = (my_army[1]) as u10;
    let adversary_tanks = adversary_army[2] as u10;
    let battle2_output = battle_clash(my_artillery, adversary_tanks);
    battle_points += battle2_output as u2;

    // Rule3: Tanks beats Infantry
    let my_tanks = (my_army[2]) as u10;
    let adversary_infantry = adversary_army[0] as u10;
    let battle3_output = battle_clash(my_tanks, adversary_infantry);
    battle_points += battle3_output as u2;

    // If my army gets >=2 points then I win --> 1 otherwise I lose --> 0
    if battle_points >= 2 { 1 } else { 0 }
}

//
//  Circuit that validates battle output of a player against his/her adversary's army.
//
//  Inputs:
//      my_army_hash { pub Field } - The pedersen hash of my_army
//     
//      my_army { [Field; 3] } - army[0] --> infantry population
//                             - army[1] --> artillery population 
//                             - army[2] --> tanks population
//  
//      adversary_army { pub [Field; 3] } - army[0] --> infantry population
//                                    - army[1] --> artillery population 
//                                    - army[2] --> tanks population 
//
//      battle_result { pub Field } - The battle result to be validated.
//
fn main(
    my_army_hash: pub Field,
    my_army: [Field; 3],
    adversary_army: pub [Field; 3],
    battle_result: pub Field
) {
    // The army hash integrity check asserts validity of the army
    let my_army_computed_hash = std::hash::pedersen_hash(my_army);
    assert(my_army_computed_hash == my_army_hash, "Your army hash integrity check failed!");

    let computed_battle_result = attack(my_army, adversary_army);
    assert(computed_battle_result == battle_result, "Non-compliant battle output");
}

/// BATTLE CIRCUIT TESTS ///

#[test]
fn test_valid_battle1() {
    let my_army = [200, 300, 500];
    let my_army_hash = std::hash::pedersen_hash(my_army);

    let adversary_army = [200, 300, 500];

    let expected_battle_result = 0;
    main(my_army_hash, my_army, adversary_army, expected_battle_result);
}

#[test]
fn test_valid_battle2() {
    let my_army = [400, 250, 350];
    let my_army_hash = std::hash::pedersen_hash(my_army);

    let adversary_army = [100, 200, 700];

    let expected_battle_result = 1;
    main(my_army_hash, my_army, adversary_army, expected_battle_result);
}

#[test]
fn test_valid_battle3() {
    let my_army = [100, 150, 750];
    let my_army_hash = std::hash::pedersen_hash(my_army);

    let adversary_army = [400, 250, 350];

    let expected_battle_result = 0;
    main(my_army_hash, my_army, adversary_army, expected_battle_result);
}

#[test]
fn test_valid_battle4() {
    let my_army = [100, 150, 750];
    let my_army_hash = std::hash::pedersen_hash(my_army);

    let adversary_army = [500, 200, 300];

    // equality following battle rules returns a win point
    let expected_battle_result = 0;
    main(my_army_hash, my_army, adversary_army, expected_battle_result);
}

#[test]
fn test_valid_battle5() {
    let my_army = [900, 50, 50];
    let my_army_hash = std::hash::pedersen_hash(my_army);

    let adversary_army = [150, 700, 150];

    let expected_battle_result = 0;
    main(my_army_hash, my_army, adversary_army, expected_battle_result);
}

#[test(should_fail_with = "Non-compliant battle output")]
fn test_invalid_battle() {
    let my_army = [200, 300, 500];
    let my_army_hash = std::hash::pedersen_hash(my_army);

    let adversary_army = [200, 300, 500];

    let expected_battle_result = 1;
    main(my_army_hash, my_army, adversary_army, expected_battle_result);
}

#[test(should_fail_with = "Your army hash integrity check failed!")]
fn test_invalid_player_army_hash() {
    let my_army = [200, 300, 500];
    let my_army_hash = std::hash::pedersen_hash([300, 400, 300]);

    let adversary_army = [200, 300, 500];

    let expected_battle_result = 1;
    main(my_army_hash, my_army, adversary_army, expected_battle_result);
}
