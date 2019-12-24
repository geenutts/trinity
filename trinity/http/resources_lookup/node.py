from aiohttp import web

from ssz.tools import (
    to_formatted_dict,
)

from eth2.beacon.types.forks import Fork
from trinity.http.resources_lookup.base import BaseResource


class Node(BaseResource):
    def version(self, request: web.Request) -> str:
        # TODO: add version number
        return "Trinity"

    def genesis_time(self, request: web.Request) -> int:
        state = self.chain.get_head_state()
        return int(state.genesis_time)

    def syncing(self, request: web.Request) -> Fork:
        # TODO
        ...

    def fork(self, request: web.Request) -> Fork:
        return to_formatted_dict(self.chain.get_head_state().fork, sedes=Fork)
