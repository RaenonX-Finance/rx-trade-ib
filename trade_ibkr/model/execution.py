from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import DefaultDict, Iterable

import numpy as np
import pandas as pd
from ibapi.contract import Contract
from pandas import DataFrame

from trade_ibkr.enums import OrderSideConst, ExecutionDataCol
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

    epoch_sec: float = field(init=False)

    def __post_init__(self):
        # noinspection PyTypeChecker
        self.epoch_sec = (
            pd.Timestamp(self.time_completed, tz="America/Chicago").tz_convert("UTC").tz_localize(None).timestamp()
        )

    @staticmethod
    def from_executions(executions: list[OrderExecution]) -> "GroupedOrderExecution":
        contract = executions[0].contract
        time_completed = max(executions, key=lambda execution: execution.time).time
        side = executions[0].side
        quantity = max(execution.cumulative_quantity for execution in executions)
        avg_price = max((execution for execution in executions), key=lambda item: item.avg_price).avg_price
        realized_pnl = sum(
            [execution.realized_pnl for execution in executions if execution.realized_pnl] +
            [0]  # All executions_df may not have realized PnL if it's a trade entry
        )

        return GroupedOrderExecution(
            contract=contract,
            time_completed=time_completed,
            side=side,
            quantity=quantity,
            avg_price=avg_price,
            realized_pnl=realized_pnl if realized_pnl else None,
        )


OrderExecutionGroupKey = tuple[int, int, OrderSideConst, int]


class OrderExecutionCollection:
    def _init_grouped_executions(self, order_execs: Iterable[OrderExecution], period_sec: int):
        grouped_executions: DefaultDict[OrderExecutionGroupKey, list[OrderExecution]] = defaultdict(list)
        for execution in order_execs:
            key = (
                int(execution.time.timestamp() / period_sec),
                execution.order_id,
                execution.side,
                get_contract_identifier(execution.contract),
            )
            grouped_executions[key].append(execution)

        for key in sorted(grouped_executions):
            _, _, _, contract_identifier = key
            grouped = grouped_executions[key]

            self._executions[contract_identifier].append(GroupedOrderExecution.from_executions(grouped))

    @staticmethod
    def _init_exec_dataframe_single(grouped_executions: list[GroupedOrderExecution]) -> DataFrame:
        df = DataFrame(grouped_executions)

        df[ExecutionDataCol.PROFIT] = (df[ExecutionDataCol.REALIZED_PNL] > 0).cumsum()
        df[ExecutionDataCol.LOSS] = (df[ExecutionDataCol.REALIZED_PNL] < 0).cumsum()
        df[ExecutionDataCol.WIN_RATE] = df[ExecutionDataCol.PROFIT].divide(
            df[ExecutionDataCol.PROFIT] + df[ExecutionDataCol.LOSS]
        )

        df[ExecutionDataCol.TOTAL_PROFIT] = (
            df[df[ExecutionDataCol.REALIZED_PNL] > 0][ExecutionDataCol.REALIZED_PNL].cumsum()
        )
        df[ExecutionDataCol.TOTAL_PROFIT].fillna(0, inplace=True)
        df[ExecutionDataCol.AVG_TOTAL_PROFIT] = df[ExecutionDataCol.TOTAL_PROFIT] \
            .divide(df[ExecutionDataCol.PROFIT]) \
            .replace(0, np.nan) \
            .fillna(method="ffill")

        df[ExecutionDataCol.TOTAL_LOSS] = (
            df[df[ExecutionDataCol.REALIZED_PNL] < 0][ExecutionDataCol.REALIZED_PNL].cumsum()
        )
        df[ExecutionDataCol.TOTAL_LOSS].fillna(0, inplace=True)
        df[ExecutionDataCol.AVG_TOTAL_LOSS] = df[ExecutionDataCol.TOTAL_LOSS] \
            .divide(df[ExecutionDataCol.LOSS]) \
            .replace(0, np.nan) \
            .fillna(method="ffill")

        df[ExecutionDataCol.AVG_TOTAL_RR_RATIO] = abs(
            df[ExecutionDataCol.AVG_TOTAL_PROFIT].divide(df[ExecutionDataCol.AVG_TOTAL_LOSS])
        )
        df[ExecutionDataCol.THRESHOLD_WIN_RATE] = np.divide(
            1,
            1 + df[ExecutionDataCol.AVG_TOTAL_RR_RATIO],
        )

        df[ExecutionDataCol.TOTAL_PNL] = df[ExecutionDataCol.REALIZED_PNL].cumsum()

        # Remove NaNs
        df.fillna(np.nan, inplace=True)
        df.replace([np.nan, np.inf, -np.inf], None, inplace=True)

        return df

    def _init_exec_dataframe(self):
        for identifier, grouped_executions in self._executions.items():
            self._executions_dataframe[identifier] = self._init_exec_dataframe_single(grouped_executions)

    def __init__(self, order_execs: Iterable[OrderExecution], period_sec: int):
        self._executions: DefaultDict[int, list[GroupedOrderExecution]] = defaultdict(list)
        self._init_grouped_executions(order_execs, period_sec)

        self._executions_dataframe: dict[int, DataFrame] = {}
        self._init_exec_dataframe()

    def print_executions(self):
        for executions in self._executions.values():
            for execution in executions:
                print(execution.contract.localSymbol, execution.time_completed, execution.avg_price,
                      execution.quantity, execution.realized_pnl)

    @property
    def executions(self) -> dict[int, list[GroupedOrderExecution]]:
        return self._executions

    @property
    def execution_dataframes(self) -> dict[int, DataFrame]:
        return self._executions_dataframe
