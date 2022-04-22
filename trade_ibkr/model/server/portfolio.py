from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Coroutine, Optional, TYPE_CHECKING

from trade_ibkr.const import EXECUTION_SMA_PERIOD
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
    px_data_list: Optional[list["PxData"]] = field(default=None)

    earliest_time: datetime = field(init=False)
    contract_ids: set[int] = field(init=False)

    px_data_dict_execution_period_sec: dict[int, "PxData"] = field(init=False)

    def __post_init__(self):
        self.px_data_dict_execution_period_sec: dict[int, "PxData"] = {}

        if not self.px_data_list:
            self.earliest_time = datetime.min
            self.contract_ids = set()
        else:
            self.earliest_time = min(px_data.earliest_time for px_data in self.px_data_list)
            self.contract_ids = {px_data.contract_identifier for px_data in self.px_data_list}

            for px_data in self.px_data_list:
                period_sec = EXECUTION_SMA_PERIOD.get(px_data.contract_symbol, EXECUTION_SMA_PERIOD["default"])

                if px_data.period_sec == period_sec:
                    self.px_data_dict_execution_period_sec[px_data.contract_identifier] = px_data

    @property
    def specified_px_data_list(self) -> bool:
        return bool(self.px_data_list)


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
