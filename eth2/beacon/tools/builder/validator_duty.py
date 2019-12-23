from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from eth_typing import BLSPubkey
from eth_utils import ValidationError, encode_hex, to_tuple

from eth2.beacon.committee_helpers import (
    get_beacon_proposer_index,
    iterate_committees_at_epoch,
)
from eth2.beacon.state_machines.base import BaseBeaconStateMachine
from eth2.beacon.types.states import BeaconState
from eth2.beacon.typing import CommitteeIndex, Epoch, Slot, ValidatorIndex
from eth2.configs import CommitteeConfig, Eth2Config


@dataclass(frozen=True)
class ValidatorDuty:
    validator_pubkey: BLSPubkey
    attestation_slot: Slot
    committee_index: CommitteeIndex
    block_proposal_slot: Slot

    def to_encoded_dict(self) -> Dict[str, Any]:
        return {
            "validator_pubkey": encode_hex(self.validator_pubkey),
            "attestation_slot": self.attestation_slot,
            "committee_index": self.committee_index,
            "block_proposal_slot": self.block_proposal_slot,
        }


@to_tuple
def get_validator_duties(
    state: BeaconState,
    state_machine: BaseBeaconStateMachine,
    epoch: Epoch,
    config: Eth2Config,
    validator_index: Optional[ValidatorIndex] = None,
) -> Iterable[Dict[str, Any]]:
    current_epoch = state.current_epoch(config.SLOTS_PER_EPOCH)
    next_epoch = state.next_epoch(config.SLOTS_PER_EPOCH)

    if validator_index is not None:
        validator_pubkey = state.validators[validator_index].pubkey

    if epoch < current_epoch:
        raise ValidationError(
            f"Epoch for committee assignment ({epoch})"
            f" must not be before current epoch {current_epoch}."
        )
    elif epoch > next_epoch:
        raise ValidationError(
            f"Epoch for committee assignment ({epoch}) must not be after next epoch {next_epoch}."
        )

    for committee, committee_index, slot in iterate_committees_at_epoch(
        state, epoch, CommitteeConfig(config)
    ):
        if slot < state.slot:
            continue

        state = state_machine.state_transition.apply_state_transition(
            state, future_slot=slot
        )

        # Get duty of certain validator.
        if validator_index in committee:
            proposer_index = get_beacon_proposer_index(state, CommitteeConfig(config))
            yield _get_validator_duty(
                validator_index, slot, proposer_index, validator_pubkey, committee_index
            )
        else:
            proposer_index = get_beacon_proposer_index(state, CommitteeConfig(config))
            for validator_index in committee:
                pubkey = state.validators[validator_index].pubkey
                yield _get_validator_duty(
                    validator_index, slot, proposer_index, pubkey, committee_index
                )


def _get_validator_duty(
    validator_index: ValidatorIndex,
    slot: Slot,
    proposer_index: ValidatorIndex,
    pubkey: BLSPubkey,
    committee_index: CommitteeIndex,
) -> Dict[str, Any]:
    proposal_slot = slot if proposer_index == validator_index else None
    duty = ValidatorDuty(
        validator_pubkey=pubkey,
        attestation_slot=slot,
        committee_index=committee_index,
        block_proposal_slot=proposal_slot,
    )
    return duty.to_encoded_dict()
