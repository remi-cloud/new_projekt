"""Broker adapters registry."""

from __future__ import annotations

from app.execution.brokers.etoro import EtoroAdapter
from app.execution.brokers.ibkr import IbkrAdapter
from app.execution.brokers.kraken import KrakenAdapter
from app.execution.brokers.nexo import NexoAdapter

_ADAPTERS = {
    "ibkr": IbkrAdapter,
    "etoro": EtoroAdapter,
    "kraken": KrakenAdapter,
    "nexo": NexoAdapter,
}

_instances: dict[str, object] = {}


def get_broker_adapter(broker_id: str):
    if broker_id not in _ADAPTERS:
        raise KeyError(f"Unknown broker: {broker_id}")
    if broker_id not in _instances:
        _instances[broker_id] = _ADAPTERS[broker_id]()
    return _instances[broker_id]


def all_broker_adapters() -> list:
    return [get_broker_adapter(bid) for bid in _ADAPTERS]
