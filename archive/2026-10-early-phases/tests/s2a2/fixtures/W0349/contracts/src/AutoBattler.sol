//SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./IAutoBattler.sol";

contract AutoBattler is IAutoBattler {

    uint public constant ARMY_SIZE = 1000;

    /// CONSTRUCTOR ///
    
    /**
     * Construct new instance of AutoBattler manager
     *
     * @param _armyVerifierAddress address - the address of the initial army validity prover
     * @param _battleVerifierAddress address - the address of the battle report prover
     */
    constructor(address _armyVerifierAddress, address _battleVerifierAddress) {
        armyVerifier = IArmyVerifier(_armyVerifierAddress);
        battleVerifier = IBattleVerifier(_battleVerifierAddress);
        gameRecord.attackNonce = 0;
    }

    /// FUNCTIONS ///

    function buildCity(bytes memory _proof, bytes32 _defenseArmyHash) external override canBuild {
        // Validate player's army configuration and update defenseArmyHash
        _defendCity(_proof, _defenseArmyHash);

        // Set up a default city
        City memory city;
        city.points = 0;
        city.cityStatus = CityStatus.InPeace;
        city.target = address(0);
        city.attacker = address(0);
        city.attackedAt = 0;

        // Add the new city to the game record
        gameRecord.player[msg.sender] = city;
    }

    function deployNewDefenseArmy(bytes memory _proof, bytes32 _defenseArmyHash) external override isPlayer isDefeated {
        // Validate player's army configuration and update defenseArmyHash
        _defendCity(_proof, _defenseArmyHash);

        // Update city status
        gameRecord.player[msg.sender].cityStatus = CityStatus.InPeace;
    }

    function attack(address _target, Army memory _attackerArmy)
        external
        override
        isPlayer
        canAttack
        isAttackable(_target)
    {   
        // validate the composition of the attacking army
        uint totalArmyCount = _attackerArmy.tanks + _attackerArmy.artillery + _attackerArmy.infantry;
        require(totalArmyCount == ARMY_SIZE, "Army size exceeds limit!");

        // Fetch the target's city
        City storage defenderCity = gameRecord.player[_target];

        // Update the city state of the target player
        defenderCity.cityStatus = CityStatus.UnderAttack;
        defenderCity.attacker = msg.sender;
        defenderCity.attackedAt = block.timestamp;
        defenderCity.attackingArmy = _attackerArmy;

        // Update the city state of the attacking player
        City storage attackerCity = gameRecord.player[msg.sender];
        attackerCity.target = _target;

        // Increment the attack nonce
        gameRecord.attackNonce++;

        // Emit battle/clash event
        emit Clash(msg.sender, _target, gameRecord.attackNonce);
    }

    function reportAttack(uint battle_result, bytes calldata _proof) external override isPlayer isUnderAttack {
        // Assert battle result is zero or one 
        require(battle_result == 0 || battle_result == 1, "Battle result must be zero or one");
        
        // Fetch the defender's city(the caller)
        City storage defenderCity = gameRecord.player[msg.sender];

        // Fetch the attacker's address and then city
        address attacker_address = defenderCity.attacker;
        City storage attackerCity = gameRecord.player[attacker_address];
        
        // Fetch the attacker's city Army
        Army memory attacker_army = defenderCity.attackingArmy;

        /*
         * Set up the public inputs for the battle verifier
         * - The defenseArmyHash public input proves the integrity of the off-chain defender's army
         * - The Army public input proves that the reported has fetched the correct army and not a different one
         * - The battle result proves the honesty of the defender's report 
         */  
        bytes32[] memory publicInputs = new bytes32[](5);
        publicInputs[0] = defenderCity.defenseArmyHash;
        publicInputs[1] = bytes32(attacker_army.infantry);
        publicInputs[2] = bytes32(attacker_army.artillery);
        publicInputs[3] = bytes32(attacker_army.tanks);
        publicInputs[4] = bytes32(battle_result);
        
        // Check if the battle proof is valid
        if (!battleVerifier.verify(_proof, publicInputs)) {
            revert("Invalid attack report proof");
        } 

        if (battle_result == 0) {
            // Update the city state of the defender player(the caller)
            defenderCity.cityStatus = CityStatus.Destroyed;
            defenderCity.attacker = address(0);
            defenderCity.attackedAt = 0;
            defenderCity.attackingArmy = Army(0, 0, 0);

            // Update the city state of the attacking player
            attackerCity.target = address(0);
            attackerCity.points += 1;

            // Emit event that the attacking player has destroyed the caller
            emit Destroyed(msg.sender, gameRecord.attackNonce);
        } else {
            // Update the city state of the defender player(the caller)
            defenderCity.cityStatus = CityStatus.Defended;
            defenderCity.attacker = address(0);
            defenderCity.attackedAt = 0;
            defenderCity.attackingArmy = Army(0, 0, 0);
            defenderCity.points += 1;

            // Update the city state of the attacking player
            attackerCity.target = address(0);

            // Emit event that the defender(caller) has successfully defender his city
            emit Defended(msg.sender, gameRecord.attackNonce);
        }
    }

    /**
     * The defender calls this method in case he/she want to surrender to the attacker.
     */
    function surrender() external override isPlayer isUnderAttack {
        // Fetch the target's city
        City storage defenderCity = gameRecord.player[msg.sender];

        // Update the city state of the current player
        defenderCity.cityStatus = CityStatus.Surrendered;
        defenderCity.attacker = address(0);
        defenderCity.attackedAt = 0;
        defenderCity.attackingArmy = Army(0, 0, 0);

        // Update the city state of the attacking player
        City storage attackerCity = gameRecord.player[defenderCity.attacker];
        attackerCity.target = address(0);

        // Increment attacker's points
        attackerCity.points += 1;

        // Emit surrender event
        emit Surrendered(msg.sender, gameRecord.attackNonce);
    }

    /**
     * If this player's target does not report battle result within 24 hours then the message sender
     * calls this method to claim his/her battle points.
     *
     * Note: With a proper UI the attacker can track his target and hence he/she would be 
     * notified to call this method.
     */
    function lootCity() external override isPlayer {
        // Fetch the target's player address
        City memory attackerCity = gameRecord.player[msg.sender];
        address target = attackerCity.target;

        // Fetch the target's city data
        City storage defenderCity = gameRecord.player[target];

        // Check if the target has not reported the battle result within one day
        if (defenderCity.attackedAt + 1 days > block.timestamp) {
            revert("Surrender period has not passed");
        }

        // Update the city state of the target's city(defender)
        defenderCity.cityStatus = CityStatus.Surrendered;
        defenderCity.attacker = address(0);
        defenderCity.attackedAt = 0;
        defenderCity.attackingArmy = Army(0, 0, 0);

        // Update the city state of the attacking player(the caller)
        attackerCity.target = address(0);
        attackerCity.points += 1;

        // Emit Looted event
        emit Looted(msg.sender, gameRecord.attackNonce);
    }

    function findAttackableCity() external view override returns (address) {
        require(gameRecord.attackable.length > 0, "Cannot find any attackable city!");

        // Generate a pseudo-random number using block timestamp and contract address
        uint256 randomNumber = uint256(keccak256(abi.encodePacked(block.timestamp, address(this))));
        uint256 randomIndex = randomNumber % gameRecord.attackable.length;

        return gameRecord.attackable[randomIndex];
    }

    /// VIEWS ///

    /**
     * Helper function that return print a player's city.
     * @param _player address - the address of the player
     */
    function playerState(address _player)
        external
        view
        override
        returns (
            bytes32 _defenseArmyHash,
            CityStatus _cityStatus,
            uint256 _points,
            address _attacker,
            uint256 _attackedAt,
            address _target,
            Army memory _attackingArmy
        )
    {
        _defenseArmyHash = gameRecord.player[_player].defenseArmyHash;
        _cityStatus = gameRecord.player[_player].cityStatus;
        _points = gameRecord.player[_player].points;
        _attacker = gameRecord.player[_player].attacker;
        _attackedAt = gameRecord.player[_player].attackedAt;
        _target = gameRecord.player[_player].target;
        _attackingArmy = gameRecord.player[_player].attackingArmy;
    }

    /// INTERNAL ///

    /**
     * Defends the city by commiting a defense army.
     *
     * @param _proof bytes memory - zk proof of valid army
     * @param _defenseArmyHash bytes32 - the army commitment pedersen hash
     */
    function _defendCity(bytes memory _proof, bytes32 _defenseArmyHash) internal {
        // Set up verifier's public input from the caller's input
        bytes32[] memory publicInputs = new bytes32[](1);
        publicInputs[0] = _defenseArmyHash;
        
        // Verify integrity of defense army configuration
        require(armyVerifier.verify(_proof, publicInputs), "Invalid Army Configuration!");

        // Update the city defenseArmyHash
        gameRecord.player[msg.sender].defenseArmyHash = _defenseArmyHash;
    }
}
