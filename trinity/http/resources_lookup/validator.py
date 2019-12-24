from typing import Tuple
from aiohttp import web

from  eth2.beacon.types.blocks import BeaconBlock
from  eth2.beacon.types.attestations import Attestation

from trinity.http.resources_lookup.base import BaseResource


class Validator(BaseResource):
    #
    # GET methods
    #
    @staticmethod
    def validator(request: web.Request) -> Tuple[str, Tuple[()]]:
        pubkey = web.Request.path.split('/')[2]
        return 'getValidator', (pubkey,)

    @staticmethod
    def duties(request: web.Request) -> Tuple[str, Tuple[()]]:
        return 'getDuties', ()

    @staticmethod
    def block(request: web.Request) -> Tuple[str, Tuple[()]]:
        return 'getBlock', ()

    @staticmethod
    def attestation(request: web.Request) -> Tuple[str, Tuple[()]]:
        return 'getAttestation', ()

    #
    # POST method
    #
    @staticmethod
    def post_block(request: web.Request) -> Tuple[str, Tuple[()]]:
        body_json = request.json()
        # TODO use Block class of the current fork.
        block = BeaconBlock(**body_json)
        return 'postBlock', (block,)

    @staticmethod
    def post_attestation(request: web.Request) -> Tuple[str, Tuple[()]]:
        body_json = request.json()
        # TODO use Attestation class of the current fork.
        attestation = Attestation(**body_json)
        return 'postAttestation', (attestation,)
