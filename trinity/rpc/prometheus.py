from typing import Any

from aiohttp import web
from prometheus_client import multiprocess
from prometheus_client import generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST, Gauge


def response_error(message: Any) -> web.Response:
    data = {'error': str(message)}
    return web.json_response(data)


import json
import logging

logger = logging.getLogger('trinity.rpc.prometheus')


rpc_command_map = {
    "beacon_head_slot": "beacon_headSlot",
    "beacon_head_root": "beacon_headRoot",
}


async def update_metrics(rpc_method, execute_rpc):
    json_request = {
        "jsonrpc": "2.0",
        "method": rpc_method,
        "params": [],
        "id": 1
    }
    rpc_reponse = await execute_rpc(json_request)
    rpc_reponse = json.loads(rpc_reponse)
    if 'error' in rpc_reponse:
        logger.debug(rpc_reponse['error'])
        return response_error(rpc_reponse['error'])
    else:
        return rpc_reponse['result']


async def metrics_handler(request, all_metrics, execute_rpc):
    """
    0: success
    1: not match
    -1: error
    """
    try:
        status = -1
        if request.path == '/metrics':
            status = 0
            logger.debug('[metrics]')
            all_metrics.total_requests.inc()
            logger.debug('[metrics] increased')


            for key, rpc_method in rpc_command_map.items():
                result = await update_metrics(rpc_method, execute_rpc)
                gauge = getattr(all_metrics, key)
                gauge.set(result)
            return 0, web.Response(body=generate_latest(all_metrics.registry), content_type='text/plain')

        elif request.path == '/beacon_head_slot':
            status = 0
            json_request = {
                "jsonrpc": "2.0",
                "method": "beacon_headSlot",
                "params": [],
                "id": 1
            }
            rpc_reponse = await execute_rpc(json_request)
            rpc_reponse = json.loads(rpc_reponse)
            if 'error' in rpc_reponse:
                logger.debug(rpc_reponse['error'])
                return response_error(rpc_reponse['error'])

            all_metrics.beacon_head_slot.set(int(rpc_reponse['result']))

        else:
            status = 1
            return status, None
    except Exception as e:
        msg = f"Error in metrics_handler: {e}"
        logger.debug(msg)
        return status, response_error(msg)
    # finally:
    #     msg = f"Unknown error in metrics_handler"
    #     logger.debug(msg)
    #     return status, response_error(msg)
