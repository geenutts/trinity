from abc import (
    ABC,
)
from typing import Any, Callable, TypeVar

from aiohttp import web
from lahja.base import EndpointAPI

from eth2.beacon.chains.base import (
    BaseBeaconChain,
)
from trinity.http.exceptions import APIServerError


TBaseResource = TypeVar("TBaseResource", bound="BaseResource")


class BaseResource(ABC):
    ...
