import logging
from typing import (
    Callable,
)

import ssz

from eth_utils import (
    ValidationError,
    encode_hex,
)

from eth.exceptions import BlockNotFound

from eth2.beacon.epoch_processing_helpers import (
    get_attesting_indices,
)
from eth2.beacon.types.aggregate_and_proof import AggregateAndProof
from eth2.beacon.types.attestations import Attestation
from eth2.beacon.chains.base import BaseBeaconChain
from eth2.beacon.types.blocks import BeaconBlock
from eth2.beacon.types.states import BeaconState
from eth2.beacon.state_machines.forks.serenity.block_validation import (
    validate_attestation,
    validate_proposer_signature,
)
from eth2.beacon.tools.builder.aggregator import (
    is_aggregator,
    validate_aggregator_proof,
)
from eth2.beacon.typing import Slot
from eth2.configs import CommitteeConfig, Eth2Config

from libp2p.peer.id import ID
from libp2p.pubsub.pb import rpc_pb2

from trinity._utils.shellart import bold_red
from trinity.protocol.bcc_libp2p.configs import ATTESTATION_PROPAGATION_SLOT_RANGE


logger = logging.getLogger('trinity.components.eth2.beacon.TopicValidator')


def get_beacon_block_validator(chain: BaseBeaconChain) -> Callable[..., bool]:
    def beacon_block_validator(msg_forwarder: ID, msg: rpc_pb2.Message) -> bool:
        try:
            block = ssz.decode(msg.data, BeaconBlock)
        except (TypeError, ssz.DeserializationError) as error:
            logger.debug(
                bold_red("Failed to decode block=%s, error=%s"),
                encode_hex(msg.data),
                str(error),
            )
            return False

        state_machine = chain.get_state_machine(block.slot - 1)
        state_transition = state_machine.state_transition
        state = chain.get_head_state()
        # Fast forward to state in future slot in order to pass
        # block.slot validity check
        state = state_transition.apply_state_transition(
            state,
            future_slot=block.slot,
        )
        try:
            validate_proposer_signature(state, block, CommitteeConfig(state_machine.config))
        except ValidationError as error:
            logger.debug(
                bold_red("Failed to validate block=%s, error=%s"),
                encode_hex(block.signing_root),
                str(error),
            )
            return False
        else:
            return True
    return beacon_block_validator


def get_beacon_attestation_validator(chain: BaseBeaconChain) -> Callable[..., bool]:
    def beacon_attestation_validator(msg_forwarder: ID, msg: rpc_pb2.Message) -> bool:
        try:
            attestation = ssz.decode(msg.data, sedes=Attestation)
        except (TypeError, ssz.DeserializationError) as error:
            # Not correctly encoded
            logger.debug(
                bold_red("Failed to validate attestation=%s, error=%s"),
                encode_hex(msg.data),
                str(error),
            )
            return False

        state_machine = chain.get_state_machine()
        config = state_machine.config
        state = chain.get_head_state()

        # Check that beacon blocks attested to by the attestation are validated
        try:
            chain.get_block_by_root(attestation.data.beacon_block_root)
        except BlockNotFound:
            logger.debug(
                bold_red(
                    "Failed to validate attestation=%s, attested block=%s is not validated yet"
                ),
                attestation,
                encode_hex(attestation.data.beacon_block_root),
            )
            return False

        # Fast forward to state in future slot in order to pass
        # attestation.data.slot validity check
        future_slot = max(
            Slot(attestation.data.slot + config.MIN_ATTESTATION_INCLUSION_DELAY),
            state.slot
        )
        try:
            future_state = state_machine.state_transition.apply_state_transition(
                state,
                future_slot=future_slot,
            )
        except ValidationError as error:
            logger.error(
                bold_red("Failed to fast forward to state at slot=%d, error=%s"),
                future_slot,
                str(error),
            )
            return False

        try:
            validate_attestation(
                future_state,
                attestation,
                config,
            )
        except ValidationError as error:
            logger.debug(
                bold_red("Failed to validate attestation=%s, error=%s"),
                attestation,
                str(error),
            )
            return False

        return True
    return beacon_attestation_validator


def validate_aggregate_and_proof(
    state: BeaconState,
    aggregate_and_proof: AggregateAndProof,
    config: Eth2Config,
) -> None:
    """
    Validate aggregate_and_proof

    Reference: https://github.com/ethereum/eth2.0-specs/blob/v09x/specs/networking/p2p-interface.md#global-topics  # noqa: E501
    """
    if (
        aggregate_and_proof.aggregate.data.slot + ATTESTATION_PROPAGATION_SLOT_RANGE < state.slot or
        aggregate_and_proof.aggregate.data.slot > state.slot
    ):
        raise ValidationError(
            "aggregate_and_proof.aggregate.data.slot should be within the last"
            " ATTESTATION_PROPAGATION_SLOT_RANGE slots. Got"
            f" aggregate_and_proof.aggregate.data.slot={aggregate_and_proof.aggregate.data.slot},"
            f" current slot={state.slot},"
            f" ATTESTATION_PROPAGATION_SLOT_RANGE={ATTESTATION_PROPAGATION_SLOT_RANGE}"
        )

    attesting_indices = get_attesting_indices(
        state,
        aggregate_and_proof.aggregate.data,
        aggregate_and_proof.aggregate.aggregation_bits,
        CommitteeConfig(config),
    )
    if aggregate_and_proof.index not in attesting_indices:
        raise ValidationError(
            f"The aggregator index ({aggregate_and_proof.index}) is not within"
            f" the aggregate's committee {attesting_indices}"
        )

    if not is_aggregator(
        state,
        aggregate_and_proof.aggregate.data.slot,
        aggregate_and_proof.aggregate.data.index,
        aggregate_and_proof.selection_proof,
        CommitteeConfig(config),
    ):
        raise ValidationError(
            f"The given validator {aggregate_and_proof.index} is not selected aggregator"
        )

    validate_aggregator_proof(state, aggregate_and_proof, CommitteeConfig(config))

    validate_attestation(state, aggregate_and_proof.aggregate, config)


def get_beacon_aggregate_and_proof_validator(chain: BaseBeaconChain) -> Callable[..., bool]:
    def beacon_aggregate_and_proof_validator(msg_forwarder: ID, msg: rpc_pb2.Message) -> bool:
        try:
            aggregate_and_proof = ssz.decode(msg.data, sedes=AggregateAndProof)
        except (TypeError, ssz.DeserializationError) as error:
            # Not correctly encoded
            logger.debug(
                bold_red("Failed to validate aggregate_and_proof=%s, error=%s"),
                encode_hex(msg.data),
                str(error),
            )
            return False

        state_machine = chain.get_state_machine()
        config = state_machine.config
        state = chain.get_head_state()

        attestation = aggregate_and_proof.aggregate

        # Check that beacon blocks attested to by the attestation are validated
        try:
            chain.get_block_by_root(attestation.data.beacon_block_root)
        except BlockNotFound:
            logger.debug(
                bold_red(
                    "Failed to validate attestation=%s, attested block=%s is not validated yet"
                ),
                attestation,
                encode_hex(attestation.data.beacon_block_root),
            )
            return False

        # Fast forward to state in future slot in order to pass
        # attestation.data.slot validity check
        future_slot = max(
            Slot(attestation.data.slot + config.MIN_ATTESTATION_INCLUSION_DELAY),
            state.slot
        )
        try:
            future_state = state_machine.state_transition.apply_state_transition(
                state,
                future_slot=future_slot,
            )
        except ValidationError as error:
            logger.error(
                bold_red("Failed to fast forward to state at slot=%d, error=%s"),
                future_slot,
                str(error),
            )
            return False

        try:
            validate_aggregate_and_proof(
                future_state,
                aggregate_and_proof,
                config,
            )
        except ValidationError as error:
            logger.debug(
                bold_red("Failed to validate aggregate_and_proof=%s, error=%s"),
                aggregate_and_proof,
                str(error),
            )
            return False

        return True
    return beacon_aggregate_and_proof_validator
