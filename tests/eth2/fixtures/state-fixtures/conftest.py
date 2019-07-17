import pytest
from eth2._utils.bls import bls
from eth2._utils.bls.backends import PyECCBackend

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
        bls.use(PyECCBackend)
    else:
        bls.use_noop_backend()
