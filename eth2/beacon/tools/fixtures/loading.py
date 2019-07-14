import os
from typing import (
    Any,
    Dict,
)

from ruamel.yaml import (
    YAML,
)

from eth2.beacon.helpers import (
    compute_epoch_of_slot,
)
from eth2.configs import (
    Eth2Config,
)

from eth2.beacon.tools.fixtures.test_file import (
    TestFile,
)


#
# Eth2Config
#
def generate_config_by_dict(dict_config: Dict[str, Any]):
    for key in list(dict_config):
        if 'DOMAIN_' in key:
            # DOMAIN is defined in SignatureDomain
            dict_config.pop(key, None)

    dict_config['GENESIS_EPOCH'] = compute_epoch_of_slot(
        dict_config['GENESIS_SLOT'],
        dict_config['SLOTS_PER_EPOCH'],
    )
    return Eth2Config(**dict_config)


def get_config(root_project_dir, config_name):
    # TODO: change the path after the constants presets are copied to submodule
    path = root_project_dir / 'tests/eth2/fixtures'
    yaml = YAML()
    file_name = config_name + '.yaml'
    file_to_open = path / file_name
    with open(file_to_open, 'U') as f:
        new_text = f.read()
        data = yaml.load(new_text)
    return generate_config_by_dict(data)


def get_all_test_files(root_project_dir, fixture_pathes, parse_test_case_fn):
    test_files = ()
    yaml = YAML()
    for path in fixture_pathes:
        entries = os.listdir(path)
        for file_name in entries:
            if 'minimal' in file_name:
                file_to_open = path / file_name
                with open(file_to_open, 'U') as f:
                    new_text = f.read()
                    data = yaml.load(new_text)
                    config_name = data['config']
                    config = get_config(root_project_dir, config_name)
                    parsed_test_cases = tuple(
                        parse_test_case_fn(test_case, config)
                        for test_case in data['test_cases']
                    )
                    test_file = TestFile(
                        file_name=file_name,
                        config=config,
                        test_cases=parsed_test_cases,
                    )
                    test_files += (test_file,)
    return test_files
