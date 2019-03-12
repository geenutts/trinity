import ssz

from eth2.beacon.chains.base import (
    BeaconChain,
)
from eth2.beacon.types.deposits import Deposit
from eth2.beacon.types.deposit_data import DepositData
from eth2.beacon.types.deposit_input import DepositInput
from eth2.beacon.types.eth1_data import Eth1Data

from eth2.beacon.on_genesis import (
    get_genesis_beacon_state,
)

from eth2.beacon.types.forks import Fork
from eth2.beacon.state_machines.forks.serenity import (
    SerenityStateMachine,
)

# buidler
from eth2.beacon.tools.builder.validator import (
    sign_proof_of_possession,
)


def get_genesis_state(config, keymap, num_validators):
    withdrawal_credentials = b'\x22' * 32
    custody_commitment = b'\x44' * 32
    fork = Fork(
        previous_version=config.GENESIS_FORK_VERSION,
        current_version=config.GENESIS_FORK_VERSION,
        epoch=config.GENESIS_EPOCH,
    )
    branch = tuple(b'\x11' * 32 for j in range(10))

    pubkeys = list(keymap)
    genesis_validator_deposits = tuple(
        Deposit(
            branch=branch,
            index=i,
            deposit_data=DepositData(
                deposit_input=DepositInput(
                    pubkey=pubkeys[i],
                    withdrawal_credentials=withdrawal_credentials,
                    proof_of_possession=sign_proof_of_possession(
                        deposit_input=DepositInput(
                            pubkey=pubkeys[i],
                            withdrawal_credentials=withdrawal_credentials,
                        ),
                        privkey=keymap[pubkeys[i]],
                        fork=fork,
                        slot=config.GENESIS_SLOT,
                        slots_per_epoch=config.SLOTS_PER_EPOCH,
                    ),
                ),
                amount=config.MAX_DEPOSIT_AMOUNT,
                timestamp=0,
            ),
        )
        for i in range(num_validators)
    )

    latest_eth1_data = Eth1Data.create_empty_data()
    genesis_time = 0

    return get_genesis_beacon_state(
        genesis_validator_deposits=genesis_validator_deposits,
        genesis_time=genesis_time,
        latest_eth1_data=latest_eth1_data,
        genesis_slot=config.GENESIS_SLOT,
        genesis_epoch=config.GENESIS_EPOCH,
        genesis_fork_version=config.GENESIS_FORK_VERSION,
        genesis_start_shard=config.GENESIS_START_SHARD,
        shard_count=config.SHARD_COUNT,
        min_seed_lookahead=config.MIN_SEED_LOOKAHEAD,
        latest_block_roots_length=config.LATEST_BLOCK_ROOTS_LENGTH,
        latest_active_index_roots_length=config.LATEST_ACTIVE_INDEX_ROOTS_LENGTH,
        slots_per_epoch=config.SLOTS_PER_EPOCH,
        max_deposit_amount=config.MAX_DEPOSIT_AMOUNT,
        latest_slashed_exit_length=config.LATEST_SLASHED_EXIT_LENGTH,
        latest_randao_mixes_length=config.LATEST_RANDAO_MIXES_LENGTH,
        activation_exit_delay=config.ACTIVATION_EXIT_DELAY,
    )


def generate_genesis_state(config, pubkeys, num_validators):
    state = get_genesis_state(config, pubkeys, num_validators)
    with open('hundred_validators_state.txt', 'w') as f:
        f.write(ssz.encode(state).hex())

    return state


#
# Chain
#
def get_sm_class(config):
    return SerenityStateMachine.configure(
        __name__='SerenityStateMachineForTesting',
        config=config,
    )


def get_chain(config, genesis_state, genesis_block, base_db):
    klass = BeaconChain.configure(
        __name__='TestChain',
        sm_configuration=(
            (config.GENESIS_SLOT, get_sm_class(config)),
        ),
        chain_id=5566,
    )

    chain = klass.from_genesis(
        base_db,
        genesis_state=genesis_state,
        genesis_block=genesis_block,
    )
    return chain
