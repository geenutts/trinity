import rlp
from rlp.sedes import (
    BigEndianInt,
    CountableList,
)
from eth2.beacon._utils.hash import (
    hash_eth2,
)
from eth2.beacon.sedes import (
    hash32,
)
from eth2.beacon.state_machines.forks.serenity.blocks import (
    SerenityBeaconBlock,
)


uint256 = BigEndianInt(256)


class GetBlocksRequest(rlp.Serializable):
    """ Simplified Wire protocol
    Removed `skip` and `reverse` fields for now
    """
    fields = [
        ('timestamp', uint256),
        ('block_root', hash32),
        ('amount', rlp.sedes.big_endian_int)
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


class GetBlocksResponse(rlp.Serializable):
    """ Returns a list of SerenityBeaconBlock
    """
    fields = [
        ('blocks', CountableList(SerenityBeaconBlock)),
    ]

    def __init__(self, blocks):
        self.blocks = blocks

    @property
    def hash(self):
        return hash_eth2(str(self.blocks) + '::salt:jhfqou213nry138o2r124124')
