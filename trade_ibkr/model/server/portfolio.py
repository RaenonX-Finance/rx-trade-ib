from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Coroutine, DefaultDict, TYPE_CHECKING

from trade_ibkr.enums import OrderSideConst

if TYPE_CHECKING:
    from trade_ibkr.model import OrderExecutionCollection, OpenOrderBook, Position, PxData


@dataclass(kw_only=True)
class OnPositionFetchedEvent:
    position: "Position"

    def __str__(self):
        return str(self.position)


OnPositionFetched = Callable[[OnPositionFetchedEvent], Coroutine[Any, Any, None]]


@dataclass(kw_only=True)
class OnOpenOrderFetchedEvent:
    open_order: "OpenOrderBook"

    def __str__(self):
        return f"{sum(len(orders) for orders in self.open_order.orders.values())}"


OnOpenOrderFetched = Callable[[OnOpenOrderFetchedEvent], Coroutine[Any, Any, None]]


@dataclass(kw_only=True)
class OnExecutionFetchedEvent:
    executions: "OrderExecutionCollection"

    proc_sec: float

    def __str__(self):
        return f"{sum(len(executions) for executions in self.executions.executions.values())} - {self.proc_sec:.3f} s"


OnExecutionFetched = Callable[[OnExecutionFetchedEvent], Coroutine[Any, Any, None]]


@dataclass(kw_only=True)
class OnExecutionFetchedParams:
    px_data_list: list["PxData"]

    earliest_time: datetime = field(init=False)
    contract_ids: set[int] = field(init=False)

    px_data_dict_lowest_period: dict[int, "PxData"] = field(init=False)

    def __post_init__(self):
        self.earliest_time = min(px_data.earliest_time for px_data in self.px_data_list)
        self.contract_ids = {px_data.contract_identifier for px_data in self.px_data_list}

        px_data_period_secs: DefaultDict[int, list[int]] = defaultdict(list)
        for px_data in self.px_data_list:
            px_data_period_secs[px_data.contract_identifier].append(px_data.period_sec)

        px_data_period_secs_min: dict[int, int] = {
            contract_identifier: min(period_secs)
            for contract_identifier, period_secs in px_data_period_secs.items()
        }

        self.px_data_dict_lowest_period = {}
        for px_data in self.px_data_list:
            contract_identifier = px_data.contract_identifier

            if px_data.period_sec == px_data_period_secs_min[contract_identifier]:
                self.px_data_dict_lowest_period[contract_identifier] = px_data


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
