import pytest
from py_ecc import bls  # noqa: F401


from eth2.beacon.tools.fixtures.bls_mock import (
    mock_bls_verify,
    mock_bls_verify_multiple,
)


#
# BLS mock
#
@pytest.fixture(autouse=True)
def mock_bls(mocker, request):
    if 'noautofixture' in request.keywords:
        return

    mocker.patch('py_ecc.bls.verify', side_effect=mock_bls_verify)
    mocker.patch('py_ecc.bls.verify_multiple', side_effect=mock_bls_verify_multiple)
