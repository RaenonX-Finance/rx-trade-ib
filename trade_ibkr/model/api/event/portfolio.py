from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Coroutine

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

    def __str__(self):
        return f"{sum(len(executions) for executions in self.executions.executions.values())}"


OnExecutionFetched = Callable[[OnExecutionFetchedEvent], Coroutine[Any, Any, None]]

OnExecutionFetchEarliestTime = Callable[[], datetime]
