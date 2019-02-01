import random

import functools

from eth.db.atomic import AtomicDB
from eth.exceptions import (
    BlockNotFound,
    # CanonicalHeadNotFound,
    # ParentNotFound,
    # StateRootNotFound,
)

from eth2.beacon.constants import (
    GENESIS_PARENT_ROOT,
)
from eth2.beacon.helpers import (
    get_beacon_proposer_index,
)

from eth2.beacon.state_machines.forks.serenity.blocks import (
    SerenityBeaconBlock,
)

# buidler
from eth2.beacon.tools.builder.proposer import (
    create_block_on_state,
)
from eth2.beacon.tools.builder.validator import (  # noqa: F401
    create_mock_signed_attestations_at_slot,
    sign_proof_of_possession,
)

from beacon_utils import (
    get_chain,
)
from distributions import (  # noqa: F401
    transform,
    exponential_distribution,
)
from message import (
    GetBlocksRequest,
    GetBlocksResponse,
)
from sim_config import Config as p



def format_receiving(f):
        @functools.wraps(f)
        def wrapper(self, obj, network_id, sender_id):
            self.print_info(
                f'Receiving {type(obj).__name__} {obj} from [V {sender_id}]'
            )
            result = f(self, obj, network_id, sender_id)
            return result
        return wrapper


class Validator(object):
    def __init__(self,
                 config,
                 genesis_state,
                 genesis_block,
                 index,
                 privkey,
                 pubkey,
                 network,
                 time_offset=5, validator_data=None):
        # Configuration
        self.config = config

        # Create a chain object
        self.chain = get_chain(config, genesis_state, genesis_block, AtomicDB())

        # Validator local data
        self.validator_index = index
        self.privkey = privkey
        self.pubkey = pubkey

        # Network
        # Give this validator a unique ID on network
        self.id = index
        # Pointer to the test p2p network
        self.network = network
        # Record of objects already received and processed
        self.received_objects = {}

        # Local time
        # This validator's clock offset (for testing purposes)
        self.time_offset = random.randrange(time_offset) - (time_offset // 2)
        self.genesis_time = self.local_timestamp
        self.handled_slots = set()  # slot

        self.output_buf = ''

    @property
    def local_timestamp(self):
        return int(self.network.time * p.PRECISION) + self.time_offset

    @property
    def current_slot(self):
        return (self.local_timestamp - self.genesis_time) // self.config.SLOT_DURATION

    @property
    def current_epoch(self):
        return self.current_slot // self.config.EPOCH_LENGTH

    @property
    def head(self):
        return self.chain.get_canonical_head()

    @property
    def parent_block(self):
        if self.head.parent_root == GENESIS_PARENT_ROOT:
            return None
        else:
            return self.chain.get_block_by_root(self.head.parent_root)

    @property
    def state_machine(self):
        return self.chain.get_state_machine(self.head)

    @property
    def state(self):
        return self.state_machine.state

    #
    # Formatting output
    #
    def print_info(self, msg):
        """ Print timestamp and validator_id as prefix
        """
        info = (
            f"[{self.network.time}] [{self.local_timestamp}] "
            f"[S {self.current_slot}] [V {self.id}] "
            f"[B {self.chain.get_canonical_head().slot}] "
        )
        # Reduce file I/O
        self.output_buf += info
        self.output_buf += msg

        # Print out immediately
        print(info, end='')
        print(msg)

    def buffer_to_output(self):
        print(self.output_buf)
        self.output_buf = ''

    def format_direct_send(self, network_id, peer_id, obj, content=None):
        self.network.direct_send(self, peer_id, obj, network_id=network_id)
        self.print_info(
            f'Sent V {peer_id} with {obj} @network_id: {network_id}, content: {content}'
        )

    def format_broadcast(self, network_id, obj, content=None):
        self.network.broadcast(self, obj, network_id=network_id)
        self.print_info(
            f'Broadcasted a {obj} @network_id: {network_id}, content: {content} '
            f'peers: {self.network.get_peers(self, network_id)}'
        )

    #
    # Messages
    #
    def on_receive(self, obj, network_id, sender_id):
        if isinstance(obj, list):
            for _obj in obj:
                self.on_receive(_obj, network_id, sender_id)
            return

        if obj.hash in self.received_objects:
            return

        if isinstance(obj, SerenityBeaconBlock):
            self.on_receive_block(obj, network_id, sender_id)
        elif isinstance(obj, GetBlocksRequest):
            self.on_receive_get_blocks_request(obj, network_id, sender_id)
        elif isinstance(obj, GetBlocksResponse):
            self.on_receive_get_blocks_response(obj, network_id, sender_id)

        self.received_objects[obj.hash] = True

    @format_receiving
    def on_receive_block(self, obj, network_id, sender_id):
        try:
            self.chain.get_block_by_root(obj.root)
        except BlockNotFound:
            pass
        else:
            return

        imported_success = True
        try:
            self.chain.import_block(obj)
        except Exception:
            imported_success = False

        self.print_info(f'imported_success: {imported_success}')
        self.format_broadcast(network_id, obj, content=None)

    @format_receiving
    def on_receive_get_blocks_request(self, obj, network_id, sender_id):
        try:
            if isinstance(obj.block, int):
                self.chain.get_block_by_slot(obj.block)
            else:
                self.chain.get_block_by_root(obj.block)
        except BlockNotFound:
            self.print_info('block is None or False: {}'.format(obj.block))
            return

        blocks = self.get_blocks(obj, obj.amount)
        if len(blocks) > 0:
            res = GetBlocksResponse(blocks)
            self.format_direct_send(
                network_id, sender_id, res,
                content=([h.root.hex() for h in blocks]))

    @format_receiving
    def on_receive_get_blocks_response(self, obj, network_id, sender_id):
        if len(obj.blocks) > 0:
            for block in obj.blocks:
                self.chain.imprt(block)

    def tick(self):
        self.tick_main()

    def tick_main(self, init_cycle=False):
        if self.current_slot not in self.handled_slots:
            if self.is_proposer(self.current_slot):
                self.print_info(f"I'm the proposer of slot {self.current_slot}")
                self.propose_block()

            self.handled_slots.add(self.current_slot)

    def is_proposer(self, slot):
        beacon_proposer_index = get_beacon_proposer_index(
            self.state.copy(
                slot=slot,
            ),
            slot,
            self.config.EPOCH_LENGTH,
            self.config.TARGET_COMMITTEE_SIZE,
            self.config.SHARD_COUNT,
        )
        return beacon_proposer_index == self.validator_index

    def propose_block(self):
        """
        Propose a block
        """
        attestations = ()
        block = create_block_on_state(
            state=self.state,
            config=self.config,
            state_machine=self.chain.get_state_machine(self.head),
            block_class=SerenityBeaconBlock,
            parent_block=self.head,
            slot=self.current_slot,
            validator_index=self.validator_index,
            privkey=self.privkey,
            attestations=attestations,
            check_proposer_index=False,
        )
        self.format_broadcast(1, block, content=None)

    def get_blocks(self, block, amount):
        """
        Get blocks around ``block``
        """
        # TODO: fix the handle skipped slot
        counter = self.chain.head.slot
        limit = (block.slot - amount + 1) if (block.slot - amount + 1) > 0 else 0
        blocks = []
        while counter >= limit:
            blocks.append(block)
            parent_root = block.parent_root
            if parent_root is GENESIS_PARENT_ROOT:
                break
            block = self.chain.get_block_by_root(parent_root)
            counter -= 1
        return blocks[::-1]
