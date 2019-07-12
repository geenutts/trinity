from typing import (
    Sequence,
    Type,
)

from eth_typing import (
    Hash32,
)

import ssz
from ssz.sedes import (
    List,
)

from eth2.beacon.constants import (
    SECONDS_PER_DAY,
)
from eth2.beacon.deposit_helpers import (
    process_deposit,
)
from eth2.beacon.committee_helpers import (
    get_compact_committees_root,
)
from eth2.beacon.helpers import (
    get_active_validator_indices,
)

from eth2.beacon.types.blocks import (
    BaseBeaconBlock,
    BeaconBlockBody,
)
from eth2.beacon.types.block_headers import (
    BeaconBlockHeader,
)
from eth2.beacon.types.deposits import Deposit
from eth2.beacon.types.deposit_data import DepositData
from eth2.beacon.types.eth1_data import Eth1Data
from eth2.beacon.types.states import BeaconState
from eth2.beacon.typing import (
    Gwei,
    Timestamp,
)
from eth2.beacon.validator_status_helpers import (
    activate_validator,
)
from eth2.configs import (
    Eth2Config,
)


def state_with_validator_digests(state: BeaconState, config: Eth2Config) -> BeaconState:
    active_validator_indices = get_active_validator_indices(
        state.validators,
        config.GENESIS_EPOCH,
    )
    active_index_root = ssz.hash_tree_root(
        active_validator_indices,
        List(ssz.uint64),
    )
    active_index_roots = (
        (active_index_root,) * config.EPOCHS_PER_HISTORICAL_VECTOR
    )
    committee_root = get_compact_committees_root(
        state,
        config.GENESIS_EPOCH,
        config,
    )
    compact_committee_roots = (
        (committee_root,) * config.EPOCHS_PER_HISTORICAL_VECTOR
    )
    return state.copy(
        active_index_roots=active_index_roots,
        compact_committee_roots=compact_committee_roots,
    )


def round_down_to_previous_multiple(amount: int, increment: int) -> int:
    return amount - amount % increment


def initialize_beacon_state_from_eth1(*,
                                      eth1_block_hash: Hash32,
                                      eth1_timestamp: Timestamp,
                                      deposits: Sequence[Deposit],
                                      config: Eth2Config) -> BeaconState:
    state = BeaconState(
        genesis_time=eth1_timestamp - eth1_timestamp % SECONDS_PER_DAY + 2 * SECONDS_PER_DAY,
        eth1_data=Eth1Data(
            block_hash=eth1_block_hash,
            deposit_count=len(deposits),
        ),
        latest_block_header=BeaconBlockHeader(
            body_root=BeaconBlockBody().root,
        ),
        config=config,
    )

    # Process genesis deposits
    for index, deposit in enumerate(deposits):
        deposit_data_list = tuple(
            deposit.data
            for deposit in deposits[:index + 1]
        )
        state = state.copy(
            eth1_data=state.eth1_data.copy(
                deposit_root=ssz.hash_tree_root(deposit_data_list, List(DepositData)),
            ),
        )
        state = process_deposit(
            state=state,
            deposit=deposit,
            config=config,
        )

    # Process genesis activations
    for validator_index in range(len(state.validators)):
        balance = state.balances[validator_index]
        effective_balance = Gwei(
            min(
                round_down_to_previous_multiple(
                    balance,
                    config.EFFECTIVE_BALANCE_INCREMENT,
                ),
                config.MAX_EFFECTIVE_BALANCE,
            )
        )

        state = state.update_validator_with_fn(
            validator_index,
            lambda v, *_: v.copy(
                effective_balance=effective_balance,
            ),
        )

        if effective_balance == config.MAX_EFFECTIVE_BALANCE:
            state = state.update_validator_with_fn(
                validator_index,
                activate_validator,
                config.GENESIS_EPOCH,
            )

    return state_with_validator_digests(
        state,
        config,
    )


def is_valid_genesis_state(state: BeaconState, config: Eth2Config) -> bool:
    if state.genesis_time < config.MIN_GENESIS_TIME:
        return False
    active_validator_count = len(get_active_validator_indices(state, config.GENESIS_EPOCH))
    if active_validator_count < config.MIN_GENESIS_ACTIVE_VALIDATOR_COUNT:
        return False
    return True


def get_genesis_block(genesis_state_root: Hash32,
                      block_class: Type[BaseBeaconBlock]) -> BaseBeaconBlock:
    return block_class(
        state_root=genesis_state_root,
    )
