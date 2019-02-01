import time
import rlp

import eth2._utils.bls as bls
from eth2.beacon._utils.hash import hash_eth2
from eth2.beacon.on_startup import (
    get_genesis_block,
)
from eth2.beacon.state_machines.forks.serenity.blocks import (
    SerenityBeaconBlock,
)
from eth2.beacon.state_machines.forks.serenity.configs import SERENITY_CONFIG
from eth2.beacon.types.states import BeaconState

from beacon_utils import (  # noqa: F401
    generate_genesis_state,
)
from networksim import (
    NetworkSimulator,
)
from progress import progress
from sim_config import Config as p
from validator import Validator


#
# Global variables
#
privkeys = tuple(int.from_bytes(
    hash_eth2(str(i).encode('utf-8'))[:4], 'big')
    for i in range(p.NUM_VALIDATORS)
)
keymap = {}  # pub -> priv
for i, k in enumerate(privkeys):
    keymap[bls.privtopub(k)] = k
    if i % 50 == 0:
        print("Generated %d keys" % i)
pubkeys = list(keymap)


def simulation():
    # Initialize NetworkSimulator
    network = NetworkSimulator(latency=p.LATENCY, reliability=p.RELIABILITY)
    network.time = p.INITIAL_TIMESTAMP

    # 1. Create genesis state
    print('Creating genesis state')
    config = SERENITY_CONFIG

    # Something bad. :'(
    config = config._replace(
        EPOCH_LENGTH=8,
        TARGET_COMMITTEE_SIZE=8,
        SHARD_COUNT=16,
        MIN_ATTESTATION_INCLUSION_DELAY=2,
    )

    # Write to file
    if p.GENERATE_STATE:
        generate_genesis_state(config, keymap, p.NUM_VALIDATORS)

    with open('hundred_validators_state.txt', 'r') as f:
        state_bytes = f.read()
        state_bytes = bytes.fromhex(state_bytes)

    genesis_state = rlp.decode(state_bytes, BeaconState)
    genesis_block = get_genesis_block(
        genesis_state.root,
        genesis_slot=config.GENESIS_SLOT,
        block_class=SerenityBeaconBlock,
    )

    print('Genesis state created')
    validators = [
        Validator(
            config,
            genesis_state,
            genesis_block,
            index,
            privkey,
            pubkey,
            network,
            time_offset=p.TIME_OFFSET,
        )
        for index, (pubkey, privkey) in enumerate(keymap.items())
    ]

    # 2. Set NetworkSimulator n
    network.agents = validators
    network.generate_peers(num_peers=p.NUM_PEERS)

    # 3. tick
    start_time = time.time()
    print(
        f'start head block slot = {validators[0].chain.get_canonical_head().slot}'
    )

    def print_result():
        print('------ [Simulation End] ------')
        print('====== Parameters ======')
        print('------ Measuration Parameters ------')
        print('Total ticks: {}'.format(p.TOTAL_TICKS))
        print('Simulation precision: {}'.format(p.PRECISION))
        print('------ System Parameters ------')
        print('Total validators num: {}'.format(p.NUM_VALIDATORS))
        print('------ Network Parameters ------')
        print('Network latency: {} sec'.format(p.LATENCY * p.PRECISION))
        print('Network reliability: {}'.format(p.RELIABILITY))
        print('Number of peers: {}'.format(p.NUM_PEERS))
        print('Number of shard peers: {}'.format(p.SHARD_NUM_PEERS))
        print('Target total shards TPS: {}'.format(p.TARGET_TOTAL_TPS))
        print('Mean tx arrival time: {}'.format(p.MEAN_TX_ARRIVAL_TIME))
        print('------ Validator Parameters ------')
        print('Validator clock offset: {}'.format(p.TIME_OFFSET))
        print('Probability of validator failure to make a block: {}'.format(
            p.PROB_CREATE_BLOCK_SUCCESS
        ))
        print('Targe block time: {} sec'.format(p.TARGET_BLOCK_TIME))
        print('Mean mining time: {} sec'.format(p.MEAN_MINING_TIME))
        print('------ Result ------')
        # print_status()
        print("--- %s seconds ---" % (time.time() - start_time))

    try:
        for i in range(p.TOTAL_TICKS):
            # Print progress bar in stderr
            progress(i, p.TOTAL_TICKS, status='Simulating.....')

            network.tick()

            if i % 100 == 0:
                print('%d ticks passed' % i)
                # print_status()
    except Exception:
        raise
    finally:
        print_result()

    print('[END]')

    return


if __name__ == "__main__":
    simulation()
