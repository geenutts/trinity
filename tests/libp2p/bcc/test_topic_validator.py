import pytest

from trinity.protocol.bcc_libp2p.configs import (
    PUBSUB_TOPIC_BEACON_ATTESTATION,
    PUBSUB_TOPIC_BEACON_BLOCK,
    PUBSUB_TOPIC_COMMITTEE_BEACON_ATTESTATION,
)


@pytest.mark.parametrize("num_nodes", (1,))
@pytest.mark.asyncio
async def test_setup_topic_validators(nodes):
    node = nodes[0]
    subnet_id = 0
    topic_1 = PUBSUB_TOPIC_BEACON_BLOCK
    topic_2 = PUBSUB_TOPIC_BEACON_ATTESTATION
    topic_3 = PUBSUB_TOPIC_COMMITTEE_BEACON_ATTESTATION.substitute(subnet_id=subnet_id)
    assert topic_1 in node.pubsub.topic_validators
    assert topic_2 in node.pubsub.topic_validators
    assert topic_3 in node.pubsub.topic_validators
