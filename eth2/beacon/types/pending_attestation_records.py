import ssz
from ssz.sedes import (
    byte_list,
    uint64,
)

from eth2.beacon.typing import (
    Slot,
    Bitfield,
)

from .attestation_data import (
    AttestationData,
)


class PendingAttestationRecord(ssz.Serializable):

    fields = [
        # Signed data
        ('data', AttestationData),
        # Attester aggregation bitfield
        ('aggregation_bitfield', byte_list),
        # Custody bitfield
        ('custody_bitfield', byte_list),
        # Slot the attestation was included
        ('slot_included', uint64),
    ]

    def __init__(self,
                 data: AttestationData,
                 aggregation_bitfield: Bitfield,
                 custody_bitfield: Bitfield,
                 slot_included: Slot) -> None:
        super().__init__(
            data=data,
            aggregation_bitfield=aggregation_bitfield,
            custody_bitfield=custody_bitfield,
            slot_included=slot_included,
        )
