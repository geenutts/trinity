import os
from pathlib import Path
from typing import (
    Optional,
    Tuple,
    Sequence,
)

from dataclasses import (
    dataclass,
    field,
)
import pytest
from ruamel.yaml import (
    YAML,
)

from eth_utils import (
    ValidationError,
)
from ssz.tools import (
    from_formatted_dict,
    to_formatted_dict,
)

from eth_utils import (
    to_tuple,
)
from py_ecc import bls  # noqa: F401
from ssz.tools import (
    from_formatted_dict,
)

from eth2.configs import (
    Eth2Config,
    Eth2GenesisConfig,
)
from eth2.beacon.db.chain import BeaconChainDB
from eth2.beacon.helpers import (
    compute_epoch_of_slot,
)
from eth2.beacon.operations.attestation_pool import AttestationPool
from eth2.beacon.state_machines.forks.serenity.blocks import SerenityBeaconBlock
from eth2.beacon.state_machines.forks.serenity import (
    SerenityStateMachine,
)
from eth2.beacon.tools.builder.proposer import (
    advance_to_slot,
)
from eth2.beacon.tools.misc.ssz_vector import (
    override_lengths,
)
from eth2.beacon.types.blocks import BeaconBlock
from eth2.beacon.types.states import BeaconState
from eth2.beacon.typing import (
    Slot,
)
from eth2.beacon.tools.fixtures.loading import (
    BaseStateTestCase,
    TestFile,
)

# Test files
ROOT_PROJECT_DIR = Path(__file__).cwd()

BASE_FIXTURE_PATH = ROOT_PROJECT_DIR / 'eth2-fixtures' / 'tests'

SANITY_FIXTURE_PATH = BASE_FIXTURE_PATH / 'sanity'
BLOCKS_FIXTURE_PATH = SANITY_FIXTURE_PATH / 'blocks'
SLOTS_FIXTURE_PATH = SANITY_FIXTURE_PATH / 'slots'
FIXTURE_PATHES = (
    BLOCKS_FIXTURE_PATH,
    SLOTS_FIXTURE_PATH,
)


# test_format
@dataclass
class SanityTestCase(BaseStateTestCase):
    slots: Slot = 0
    blocks: Tuple[BeaconBlock, ...] = field(default_factory=tuple)


# Mock bls verification for these tests
#
def mock_bls_verify(message_hash, pubkey, signature, domain):
    return True


def mock_bls_verify_multiple(pubkeys,
                             message_hashes,
                             signature,
                             domain):
    return True


@pytest.fixture(autouse=True)
def mock_bls(mocker, request):
    if 'noautofixture' in request.keywords:
        return

    mocker.patch('py_ecc.bls.verify', side_effect=mock_bls_verify)
    mocker.patch('py_ecc.bls.verify_multiple', side_effect=mock_bls_verify_multiple)


#
# Helpers for generating test suite
#
def generate_config_by_dict(dict_config):
    for key in list(dict_config):
        if 'DOMAIN_' in key:
            # DOMAIN is defined in SignatureDomain
            dict_config.pop(key, None)

    dict_config['GENESIS_EPOCH'] = compute_epoch_of_slot(
        dict_config['GENESIS_SLOT'],
        dict_config['SLOTS_PER_EPOCH'],
    )
    return Eth2Config(**dict_config)


def get_all_test_files(fixture_pathes):
    test_files = ()
    yaml = YAML()
    for path in fixture_pathes:
        print('path:', path)
        entries = os.listdir(path)
        for file_name in entries:
            if 'minimal' in file_name:
                file_to_open = path / file_name
                print('file_to_open, ', file_to_open)
                with open(file_to_open, 'U') as f:
                    new_text = f.read()
                    data = yaml.load(new_text)
                    # config = SERENITY_CONFIG
                    config_name = data['config']
                    config = get_config(config_name)
                    parsed_test_cases = tuple(
                        parse_test_case(test_case, config)
                        for test_case in data['test_cases']
                    )
                    test_file = TestFile(
                        file_name=file_name,
                        config=config,
                        test_cases=parsed_test_cases,
                    )
                    test_files += (test_file,)
    return test_files


def get_config(config_name):
    # TODO: change the path after the constants presets are copied to submodule
    path = ROOT_PROJECT_DIR / 'tests/eth2/fixtures-tests'
    yaml = YAML()
    file_name = config_name + '.yaml'
    file_to_open = path / file_name
    with open(file_to_open, 'U') as f:
        new_text = f.read()
        try:
            data = yaml.load(new_text)
        except yaml.YAMLError as exc:
            print(exc)
    return generate_config_by_dict(data)


def parse_test_case(test_case, config):
    if 'bls_setting' not in test_case or test_case['bls_setting'] == 2:
        bls_setting = False
    else:
        bls_setting = True

    description = test_case['description']
    print('description', description)
    override_lengths(config)
    pre = from_formatted_dict(test_case['pre'], BeaconState)
    if test_case['post'] is not None:
        post = from_formatted_dict(test_case['post'], BeaconState)
        is_valid = True
    else:
        is_valid = False

    if 'blocks' in test_case:
        blocks = tuple(from_formatted_dict(block, BeaconBlock) for block in test_case['blocks'])
    else:
        blocks = ()

    slots = test_case['slots'] if 'slots' in test_case else 0
    return SanityTestCase(
        line_number=test_case.lc.line,
        bls_setting=bls_setting,
        description=description,
        pre=pre,
        post=post if is_valid else None,
        is_valid=is_valid,
        slots=slots,
        blocks=blocks,
    )


def state_fixture_mark_fn(fixture_name):
    if fixture_name == 'test_transfer':
        return pytest.mark.skip(reason="has not implemented")
    else:
        return None


@to_tuple
def get_test_cases(fixture_pathes):
    # TODO: batch reading files
    test_files = get_all_test_files(fixture_pathes)
    for test_file in test_files:
        for test_case in test_file.test_cases:
            test_id = f"{test_file.file_name}::{test_case.description}:{test_case.line_number}"
            print('test_id', test_id)
            mark = state_fixture_mark_fn(test_case.description)
            if mark is not None:
                yield pytest.param(test_case, id=test_id, marks=(mark,))
            else:
                yield pytest.param(test_case, test_file.config, id=test_id)


all_test_cases = get_test_cases(FIXTURE_PATHES)


@pytest.mark.parametrize(
    "test_case, config",
    all_test_cases
)
def test_state(base_db, config, test_case):
    execute_state_transtion(test_case, config, base_db)

def execute_state_transtion(test_case, config, base_db):
    sm_class = SerenityStateMachine.configure(
        __name__='SerenityStateMachineForTesting',
        config=config,
    )
    chaindb = BeaconChainDB(base_db, Eth2GenesisConfig(config))
    attestation_pool = AttestationPool()

    post_state = test_case.pre.copy()

    sm = sm_class(chaindb, attestation_pool, None, post_state)
    post_state = advance_to_slot(sm, post_state, test_case.slots)

    if test_case.is_valid:
        for block in test_case.blocks:
            sm = sm_class(chaindb, attestation_pool, None, post_state)
            post_state, _ = sm.import_block(block)

        # Use dict diff, easier to see the diff
        dict_post_state = to_formatted_dict(post_state, BeaconState)
        dict_expected_state = to_formatted_dict(test_case.post, BeaconState)
        for key, value in dict_expected_state.items():
            if isinstance(value, list):
                value = tuple(value)
            assert dict_post_state[key] == value
    else:
        with pytest.raises(ValidationError):
            for block in test_case.blocks:
                sm = sm_class(chaindb, attestation_pool, None, post_state)
                post_state, _ = sm.import_block(block)