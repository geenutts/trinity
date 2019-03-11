import ssz
from ssz.sedes import (
    List,
    bytes32,
    uint64,
)
from eth2.beacon._utils.hash import (
    hash_eth2,
)
from eth2.beacon.state_machines.forks.serenity.blocks import (
    SerenityBeaconBlock,
)


class GetBlocksRequest(ssz.Serializable):
    """ Simplified Wire protocol
    Removed `skip` and `reverse` fields for now
    """
    fields = [
        ('timestamp', uint64),
        ('block_root', bytes32),
        ('amount', uint64)
    ]

    def __init__(self, timestamp, block_root, amount):
        self.timestamp = timestamp
        self.block_root = block_root
        self.amount = amount

    @property
    def hash(self):
        return (
            hash_eth2(
                str(self.timestamp) +
                str(self.block_root) +
                str(self.amount) +
                '::salt:jhfqou213nry138o2r124124'
            )
        )


class GetBlocksResponse(ssz.Serializable):
    """ Returns a list of SerenityBeaconBlock
    """
    fields = [
        ('blocks', List(SerenityBeaconBlock)),
    ]

    def __init__(self, blocks):
        self.blocks = blocks

    @property
    def hash(self):
        return hash_eth2(str(self.blocks) + '::salt:jhfqou213nry138o2r124124')
