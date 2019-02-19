import sys
import cProfile
import re

import time
import json

import ssz

from eth.db.atomic import AtomicDB

from eth2.beacon.state_machines.forks.serenity.blocks import (
    SerenityBeaconBlock,
)
from eth2.beacon.state_machines.forks.serenity.configs import SERENITY_CONFIG
from eth2.beacon.types.states import BeaconState
from eth2_sim.simulation.beacon_utils import (
    get_chain,
)
from eth2.beacon.tools.builder.validator import (
    get_next_epoch_committee_assignment,
)


def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size


def run():
    config = SERENITY_CONFIG
    config = config._replace(
        EPOCH_LENGTH=4,
        TARGET_COMMITTEE_SIZE=20,
        SHARD_COUNT=2,
        MIN_ATTESTATION_INCLUSION_DELAY=2,
    )
    states = ()
    blocks = ()

    json_data = open('demo_blocks.json').read()
    encoded_blocks = json.loads(json_data)
    for block in encoded_blocks:
        blocks += (ssz.decode(bytes.fromhex(block), SerenityBeaconBlock),)

    json_data = open('demo_states.json').read()
    encoded_states = json.loads(json_data)
    for state in encoded_states:
        states += (ssz.decode(bytes.fromhex(state), BeaconState),)
        break

    serialzed_state = ssz.encode(states[0])

    with open('demo_binary_state_0.json', 'wb') as outfile:
        outfile.write(serialzed_state)

    genesis_state = states[0]
    one_validator = states[0].validator_registry[0]
    hundred_validators = states[0].validator_registry
    print('size (genesis_state)', get_size(genesis_state))
    print('size (one_validator)', get_size(one_validator))
    print('size (hundred_validators)', get_size(hundred_validators))
    print('size (99 validators)', get_size(hundred_validators[1:]))
    print('size (98 validators)', get_size(hundred_validators[2:]))

    assert blocks[0].slot == 0
    assert blocks[0].parent_root == b'\x00' * 32

    chain = get_chain(config, states[0], blocks[0], AtomicDB())

    for i in range(1, 4):
        chain.import_block(blocks[i])
        print(f'block {blocks[i].slot}, attestations={blocks[i].body.attestations}')

    assert len(states[0].validator_registry) == 100

    # assignment = get_next_epoch_committee_assignment(
    #     state=states[3],
    #     config=config,
    #     validator_index=0,
    #     registry_change=False,
    # )
    # print('len(assignment.committee)', len(assignment.committee))
    # print('assignment.committee', assignment.committee)

    benchmark(blocks, chain, config)


def benchmark(blocks, chain, config):
    start = time.time()
    print('----start time----')
    for i in range(4, 8):
        if (blocks[i].slot + 1) % config.EPOCH_LENGTH == 0:
            start_epoch = time.time()
        chain.import_block(blocks[i])
        if (blocks[i].slot + 1) % config.EPOCH_LENGTH == 0:
            end_epoch = time.time()
            print(f'epoch processing time: {end_epoch - start_epoch}')
        print(f'block {blocks[i].slot}, attestations={blocks[i].body.attestations}')

    for i in range(8, 12):
        if (blocks[i].slot + 1) % config.EPOCH_LENGTH == 0:
            start_epoch = time.time()
        chain.import_block(blocks[i])
        if (blocks[i].slot + 1) % config.EPOCH_LENGTH == 0:
            end_epoch = time.time()
            print(f'epoch processing time: {end_epoch - start_epoch}')
        print(f'block {blocks[i].slot}, attestations={blocks[i].body.attestations}')

    end = time.time()
    total_time = end - start

    print(f'total time: {total_time}')


if __name__ == "__main__":
    run()
    # cProfile.run('run()', filename="result.out", sort="cumulative")
