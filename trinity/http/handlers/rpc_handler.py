import logging
from typing import (
    Any,
    Callable,
    Dict,
)

from aiohttp import web
from eth_utils.toolz import curry

from trinity.http.exceptions import (
    JsonParsingException,
    JsonRpcCallException,
)
from trinity.http.handlers.base import BaseHTTPHandler, response_error
from trinity.http.resources_lookup.beacon import Beacon
from trinity.http.resources_lookup.network import Network
from trinity.http.resources_lookup.node import Node
from trinity.http.resources_lookup.validator import Validator


ETH2_RESOURCES = (
    'beacon',
    'network'
    'node',
    'validator',
)


#
# JSON-RPC
#
async def load_json_request(request: web.Request) -> Any:
    try:
        body_json = await request.json()
    except Exception:
        raise JsonParsingException(f"Invalid request: {request}")
    else:
        return body_json


async def execute_json_rpc(
    execute_rpc: Callable[[Any], Any],
    json_request: Dict['str', Any]
) -> str:
    try:
        result = await execute_rpc(json_request)
    except Exception as e:
        msg = f"Unrecognized exception while executing RPC: {e}"
        raise JsonRpcCallException(msg)
    else:
        return result


def _lookup_by_restful_request(request):
    path = request.path.lower()
    path_array = tuple(path.split('/'))
    if len(path_array) <= 2:
        raise Exception(f"Wrong path: {path}")
    resource_name = path_array[1]
    object = path_array[2]

    if resource_name not in ETH2_RESOURCES:
        raise Exception("Resource not found")

    if request.method == 'POST':
        object = 'post_' + object

    if resource_name == 'beacon':
        resource_lookup = Beacon()
    elif resource_name == 'network':
        resource_lookup = Network()
    elif resource_name == 'node':
        resource_lookup = Node()
    elif resource_name == 'validator':
        resource_lookup = Validator()
        # TODO: handle the special case: validator/{pubkey} here

    resolver = getattr(resource_lookup, object)
    rpc_method_name, params = resolver(request)
    return resource_name, rpc_method_name, params


def _to_json_request(resource_name, rpc_method_name, params):
    return {
        "jsonrpc":"2.0",
        "method":resource_name + '_' + rpc_method_name,
        "params": params,
        "id":1
    }


class RPCHandler(BaseHTTPHandler):

    @staticmethod
    @curry
    async def handle(execute_rpc: Callable[[Any], Any], request: web.Request) -> web.Response:
        logger = logging.getLogger('trinity.http.handlers.rpc_handler.RPCHandler')
        logger.debug('Receiving %s request: %s', request.method, request.path)

        try:
            # Parse JSON-RPC
            json_request = await load_json_request(request)
        except JsonParsingException as e:
            try:
                resource_name, rpc_method_name, params =_lookup_by_restful_request(request)
                json_request = _to_json_request(resource_name, rpc_method_name, params)
            except Exception as e:
               return response_error(e)

        try:
            result = await execute_json_rpc(execute_rpc, json_request)
        except JsonRpcCallException as e:
            return response_error(e)
        else:
            return web.Response(content_type='application/json', text=result)
