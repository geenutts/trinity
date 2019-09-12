import asyncio
import logging
from typing import (
    Any,
    Callable,
)

from aiohttp import web
from eth_utils.toolz import curry

from cancel_token import (
    CancelToken,
)

from p2p.service import (
    BaseService,
)

from trinity.rpc.main import (
    RPCServer,
)

from .prometheus import metrics_handler


class JsonParsingException(Exception):
    ...


class JsonRpcCallException(Exception):
    ...


async def load_json_request(request: web.Request) -> Any:
    logger = logging.getLogger('trinity.rpc.http')
    try:
        body_json = await request.json()
    except Exception as e:
        raise JsonParsingException(f"Invalid request: {request}")
    else:
        return body_json

async def execute_json_rpc(execute_rpc, json_request):
    try:
        result = await execute_rpc(json_request)
    except Exception as e:
        msg = f"Unrecognized exception while executing RPC: {e}"
        raise JsonRpcCallException(msg)
    else:
        return result


import prometheus_client
from prometheus_client import Counter, Gauge, REGISTRY, CollectorRegistry

from prometheus_client.core import GaugeMetricFamily


class AllMetrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.total_requests = Counter('request_count', 'Total webapp request count', registry=self.registry)
        self.beacon_head_slot = Gauge('beacon_head_slot', 'Slot of the head block of the beacon chain', registry=self.registry)
        self.beacon_head_root = Gauge('beacon_head_root', 'Root of the head block of the beacon chain', registry=self.registry)

all_metrics = AllMetrics()

@curry
async def handler(execute_rpc: Callable[[Any], Any], request: web.Request) -> web.Response:
    logger = logging.getLogger('trinity.rpc.http')
    if request.method == 'POST':
        logger.debug(f'Receiving POST request: {request}')
        try:
            body_json = await load_json_request(request)
        except JsonParsingException as e:
            return response_error(e)

        try:
            result = await execute_json_rpc(execute_rpc, body_json)
        except JsonRpcCallException as e:
            return response_error(e)
        else:
            return web.Response(content_type='application/json', text=result)
    elif request.method == 'GET':
        logger.debug(f'Receiving GET request: {request.path}')
        status, response = await metrics_handler(request, all_metrics, execute_rpc)
        if status <= 0:
            return response

        all_metrics.total_requests.inc()
        return web.json_response({
            'status': 'ok'
        })
    else:
        return response_error("Request method should be POST")


def response_error(message: Any) -> web.Response:
    data = {'error': str(message)}
    return web.json_response(data)

async def hello(request):
    return web.Response(text="Hello, world")

class HTTPServer(BaseService):
    rpc = None
    server = None
    host = None
    port = None
    app = None

    def __init__(
            self,
            rpc: RPCServer,
            host: str = '127.0.0.1',
            port: int = 8545,
            token: CancelToken = None,
            loop: asyncio.AbstractEventLoop = None) -> None:
        super().__init__(token=token, loop=loop)
        self.rpc = rpc
        self.host = host
        self.port = port
        # Low-Level Server to handle the event loop by ourselves
        self.server = web.Server(handler(self.rpc.execute))


        # self.app = web.Application()
        # self.app.add_routes([web.get('/', hello)])



    async def _run(self) -> None:
        runner = web.ServerRunner(self.server)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        # web.run_app(self.app, host=self.host, port=self.port)

        await self.cancel_token.wait()

    async def _cleanup(self) -> None:
        await self.server.shutdown()
