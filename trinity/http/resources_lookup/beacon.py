from typing import Tuple
from aiohttp import web
from trinity.http.resources_lookup.base import BaseResource


class Beacon(BaseResource):
    @staticmethod
    def head(request: web.Request) -> Tuple[str, Tuple[()]]:
        return 'getHead', ()

    @staticmethod
    def block(request: web.Request) -> Tuple[str, Tuple[()]]:
        if 'slot' in request.query:
            key = request.query['slot']
        elif 'root' in request.query:
            key = request.query['root']

        return 'getBlock', (key,)

    @staticmethod
    def state(request: web.Request) -> Tuple[str, Tuple[()]]:
        if 'slot' in request.query:
            key = request.query['slot']
        elif 'root' in request.query:
            key = request.query['root']

        return 'getBlock', (key,)
