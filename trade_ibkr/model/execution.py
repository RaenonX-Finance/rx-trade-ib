from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import DefaultDict, Iterable

import pandas as pd
from ibapi.contract import Contract

from trade_ibkr.enums import OrderSideConst
from trade_ibkr.utils import get_contract_identifier


@dataclass(kw_only=True)
class OrderExecution:
    exec_id: str
    order_id: int
    contract: Contract
    local_time_original: str
    side: OrderSideConst
    cumulative_quantity: Decimal
    avg_price: float

    realized_pnl: float | None = None

    @property
    def time(self) -> datetime:
        return datetime.strptime(self.local_time_original, "%Y%m%d  %H:%M:%S")


@dataclass(kw_only=True)
class GroupedOrderExecution:
    contract: Contract
    time_completed: datetime
    side: OrderSideConst
    quantity: Decimal
    avg_price: float

    realized_pnl: float | None = None

    @staticmethod
    def from_executions(executions: list[OrderExecution]) -> "GroupedOrderExecution":
        contract = executions[0].contract
        time_completed = max(executions, key=lambda execution: execution.time).time
        side = executions[0].side
        quantity = max(execution.cumulative_quantity for execution in executions)
        avg_price = max((execution for execution in executions), key=lambda item: item.avg_price).avg_price
        realized_pnl = sum(
            [execution.realized_pnl for execution in executions if execution.realized_pnl] +
            [0]  # All executions may not have realized PnL if it's a trade entry
        )

        return GroupedOrderExecution(
            contract=contract,
            time_completed=time_completed,
            side=side,
            quantity=quantity,
            avg_price=avg_price,
            realized_pnl=realized_pnl if realized_pnl else None,
        )

    @property
    def epoch_sec(self) -> float:
        # noinspection PyTypeChecker
        return pd.Timestamp(self.time_completed, tz="America/Chicago").tz_convert("UTC").tz_localize(None).timestamp()


OrderExecutionGroupKey = tuple[int, int, OrderSideConst, int]


class OrderExecutionCollection:
    def __init__(self, order_execs: Iterable[OrderExecution], period_sec: int):
        grouped_executions: DefaultDict[OrderExecutionGroupKey, list[OrderExecution]] = defaultdict(list)
        for execution in order_execs:
            key = (
                int(execution.time.timestamp() / period_sec),
                execution.order_id,
                execution.side,
                get_contract_identifier(execution.contract),
            )
            grouped_executions[key].append(execution)

        self._executions: DefaultDict[int, list[GroupedOrderExecution]] = defaultdict(list)
        for key in sorted(grouped_executions):
            _, _, _, contract_identifier = key
            grouped = grouped_executions[key]

            self._executions[contract_identifier].append(GroupedOrderExecution.from_executions(grouped))

    def print_executions(self):
        for executions in self._executions.values():
            for execution in executions:
                print(execution.contract.localSymbol, execution.time_completed, execution.avg_price,
                      execution.quantity, execution.realized_pnl)

    @property
    def executions(self) -> dict[int, list[GroupedOrderExecution]]:
        return self._executions
