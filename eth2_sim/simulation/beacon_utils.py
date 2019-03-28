import ssz

from eth2.beacon.chains.base import (
    BeaconChain,
)

from eth2.beacon.state_machines.forks.serenity import (
    SerenityStateMachine,
)
from eth2.beacon.state_machines.forks.serenity.blocks import (
    SerenityBeaconBlock,
)

# buidler
from eth2.beacon.tools.builder.initializer import (
    create_mock_genesis,
)


def get_genesis(config, keymap, num_validators):
    return create_mock_genesis(
        num_validators=num_validators,
        config=config,
        keymap=keymap,
        genesis_block_class=SerenityBeaconBlock,
    )


def generate_genesis_state(config, pubkeys, num_validators):
    state, _ = get_genesis(config, pubkeys, num_validators)
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
