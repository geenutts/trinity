import rlp

from eth2.beacon.chains.base import (
    BeaconChain,
)
from eth2.beacon.types.deposits import Deposit
from eth2.beacon.types.deposit_data import DepositData
from eth2.beacon.types.deposit_input import DepositInput
from eth2.beacon.types.eth1_data import Eth1Data

from eth2.beacon.on_startup import (
    get_initial_beacon_state,
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
    randao_commitment = b'\x33' * 32
    custody_commitment = b'\x44' * 32
    fork = Fork(
        previous_version=config.GENESIS_FORK_VERSION,
        current_version=config.GENESIS_FORK_VERSION,
        slot=config.GENESIS_SLOT,
    )
    branch = tuple(b'\x11' * 32 for j in range(10))

    pubkeys = list(keymap)
    initial_validator_deposits = (
        Deposit(
            branch=branch,
            index=i,
            deposit_data=DepositData(
                deposit_input=DepositInput(
                    pubkey=pubkeys[i],
                    withdrawal_credentials=withdrawal_credentials,
                    randao_commitment=randao_commitment,
                    custody_commitment=custody_commitment,
                    proof_of_possession=sign_proof_of_possession(
                        deposit_input=DepositInput(
                            pubkey=pubkeys[i],
                            withdrawal_credentials=withdrawal_credentials,
                            randao_commitment=randao_commitment,
                            custody_commitment=custody_commitment,
                        ),
                        privkey=keymap[pubkeys[i]],
                        fork=fork,
                        slot=config.GENESIS_SLOT,
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

    return get_initial_beacon_state(
        initial_validator_deposits=initial_validator_deposits,
        genesis_time=genesis_time,
        latest_eth1_data=latest_eth1_data,
        genesis_slot=config.GENESIS_SLOT,
        genesis_fork_version=config.GENESIS_FORK_VERSION,
        genesis_start_shard=config.GENESIS_START_SHARD,
        shard_count=config.SHARD_COUNT,
        latest_block_roots_length=config.LATEST_BLOCK_ROOTS_LENGTH,
        latest_index_roots_length=config.LATEST_INDEX_ROOTS_LENGTH,
        epoch_length=config.EPOCH_LENGTH,
        max_deposit_amount=config.MAX_DEPOSIT_AMOUNT,
        latest_penalized_exit_length=config.LATEST_PENALIZED_EXIT_LENGTH,
        latest_randao_mixes_length=config.LATEST_RANDAO_MIXES_LENGTH,
        entry_exit_delay=config.ENTRY_EXIT_DELAY,
    )


def generate_genesis_state(config, pubkeys, num_validators):
    state = get_genesis_state(config, pubkeys, num_validators)
    with open('hundred_validators_state.txt', 'w') as f:
        f.write(rlp.encode(state).hex())

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
            (0, get_sm_class(config)),
        ),
        chain_id=5566,
    )

    chain = klass.from_genesis(
        base_db,
        genesis_state=genesis_state,
        genesis_block=genesis_block,
    )
    assert chain.get_canonical_block_by_slot(0) == genesis_block
    return chain

#
# Main
#
# def sim(keymap):
#     config = SERENITY_CONFIG

#     # Something bad. :'(
#     config = config._replace(
#         EPOCH_LENGTH=8,
#         TARGET_COMMITTEE_SIZE=32,
#         SHARD_COUNT=4,
#         MIN_ATTESTATION_INCLUSION_DELAY=2,
#     )

#     genesis_state = generate_genesis_state(config, keymap)

#     with open('hundred_validators_state.txt', 'r') as f:
#         state_bytes = f.read()
#         state_bytes = bytes.fromhex(state_bytes)

#     genesis_state = rlp.decode(state_bytes, BeaconState)

#     genesis_block = get_genesis_block(
#         genesis_state.root,
#         genesis_slot=config.GENESIS_SLOT,
#         block_class=SerenityBeaconBlock,
#     )
#     assert genesis_block.slot == 0

#     base_db = AtomicDB()
#     chain = get_chain(config, genesis_state, genesis_block, base_db)

#     blocks = (genesis_block,)
#     state = genesis_state
#     num_slots = config.EPOCH_LENGTH * 3

#     attestations = ()
#     for current_slot in range(1, num_slots):

#         # Propose a block
#         block = create_mock_block(
#             state=state,
#             config=config,
#             state_machine=chain.get_state_machine(blocks[-1]),
#             block_class=SerenityBeaconBlock,
#             parent_block=blocks[-1],
#             keymap=keymap,
#             slot=current_slot,
#             attestations=attestations,
#         )

#         # Put to chain
#         chain.import_block(block)
#         state = chain.get_state_machine(block).state


#         assert block != genesis_block
#         assert block == chain.get_canonical_block_by_slot(current_slot)


#         blocks += (block,)
#         print(
#             f"{block}: slot={block.slot}"
#             f"\t{state}: slot={state.slot}"
#         )

#         if current_slot > config.MIN_ATTESTATION_INCLUSION_DELAY:
#             attestation_slot = current_slot - config.MIN_ATTESTATION_INCLUSION_DELAY
#             attestations = create_mock_signed_attestations_at_slot(
#                 state,
#                 config,
#                 attestation_slot,
#                 keymap,
#                 1.0,
#             )
#         else:
#             attestations = ()


# if __name__ == '__main__':
#     sim()
