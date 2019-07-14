from typing import (
    Sequence,
)

from eth_typing import (
    BLSPubkey,
    BLSSignature,
    Hash32,
)


def mock_bls_verify(message_hash: Hash32,
                    pubkey: BLSPubkey,
                    signature: BLSSignature,
                    domain: int) -> bool:
    return True


def mock_bls_verify_multiple(pubkeys: Sequence[BLSPubkey],
                             message_hashes: Sequence[Hash32],
                             signature: BLSSignature,
                             domain: int) -> bool:
    return True
