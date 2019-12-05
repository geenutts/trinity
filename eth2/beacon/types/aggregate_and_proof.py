from eth_typing import BLSSignature
from eth_utils import humanize_hash
import ssz
from ssz.sedes import bytes96, uint64

from eth2.beacon.constants import EMPTY_SIGNATURE
from eth2.beacon.types.attestations import Attestation, default_attestation
from eth2.beacon.types.defaults import default_validator_index
from eth2.beacon.typing import ValidatorIndex


class AggregateAndProof(ssz.Serializable):

    fields = [
        ("aggregator_index", uint64),
        ("aggregate", Attestation),
        ("selection_proof", bytes96),
    ]

    def __init__(
        self,
        aggregator_index: ValidatorIndex = default_validator_index,
        aggregate: Attestation = default_attestation,
        selection_proof: BLSSignature = EMPTY_SIGNATURE,
    ) -> None:
        super().__init__(
            aggregator_index=aggregator_index,
            aggregate=aggregate,
            selection_proof=selection_proof,
        )

    def __str__(self) -> str:
        return (
            f"aggregator_index={self.aggregator_index},"
            f" aggregate={self.aggregate},"
            f" selection_proof={humanize_hash(self.selection_proof)},"
        )


default_aggregate_and_proof = AggregateAndProof()
