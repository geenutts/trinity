from typing import Tuple
from aiohttp import web
from trinity.http.resources_lookup.base import BaseResource


class Network(BaseResource):
    @staticmethod
    def peer_id(request: web.Request) -> Tuple[str, Tuple[()]]:
        return "getPeerId", ()

    @staticmethod
    def peers(request: web.Request) -> Tuple[str, Tuple[()]]:
        return "getPeers", ()

    @staticmethod
    def enr(request: web.Request) -> Tuple[str, Tuple[()]]:
        return "getEnr", ()
