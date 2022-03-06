from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Coroutine

from trade_ibkr.enums import OrderSideConst
from ...execution import OrderExecutionCollection
from ...open_order import OpenOrderBook
from ...position import Position


@dataclass(kw_only=True)
class OnPositionFetchedEvent:
    position: Position


OnPositionFetched = Callable[[OnPositionFetchedEvent], Coroutine[Any, Any, None]]


@dataclass(kw_only=True)
class OnOpenOrderFetchedEvent:
    open_order: OpenOrderBook

    def __str__(self):
        return f"{sum(len(orders) for orders in self.open_order.orders.values())}"


OnOpenOrderFetched = Callable[[OnOpenOrderFetchedEvent], Coroutine[Any, Any, None]]


@dataclass(kw_only=True)
class OnExecutionFetchedEvent:
    executions: OrderExecutionCollection

    proc_sec: float

    def __str__(self):
        return f"{sum(len(executions) for executions in self.executions.executions.values())} - {self.proc_sec:.3f} s"


OnExecutionFetched = Callable[[OnExecutionFetchedEvent], Coroutine[Any, Any, None]]


@dataclass(kw_only=True)
class OnExecutionFetchedParams:
    earliest_time: datetime
    contract_ids: set[int]


OnExecutionFetchedGetParams = Callable[[], OnExecutionFetchedParams]


@dataclass(kw_only=True)
class OnOrderFilledEvent:
    identifier: int
    symbol: str
    action: OrderSideConst
    quantity: Decimal
    fill_px: float

    def __str__(self):
        return f"{self.symbol} {self.action} {self.quantity} @ {self.fill_px:.2f}"


OnOrderFilled = Callable[[OnOrderFilledEvent], Coroutine[Any, Any, None]]
