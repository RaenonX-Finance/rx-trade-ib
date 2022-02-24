from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import DefaultDict, Iterable

import numpy as np
import pandas as pd
from ibapi.contract import Contract
from pandas import DataFrame

from trade_ibkr.enums import ExecutionDataCol, ExecutionSideConst
from trade_ibkr.utils import get_contract_identifier


@dataclass(kw_only=True)
class OrderExecution:
    exec_id: str
    order_id: int
    contract: Contract
    local_time_original: str
    side: ExecutionSideConst
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
    side: ExecutionSideConst
    quantity: Decimal
    avg_price: float

    realized_pnl: float | None = None

    epoch_sec: float = field(init=False)

    def __post_init__(self):
        # noinspection PyTypeChecker
        self.epoch_sec = (
            pd.Timestamp(self.time_completed, tz="America/Chicago").tz_convert("UTC").tz_localize(None).timestamp()
        )

    @property
    def signed_quantity(self) -> Decimal:
        return self.quantity * (1 if self.side == "BOT" else -1)

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

    def to_closing_and_opening(self, closing_qty: Decimal) -> tuple["GroupedOrderExecution", "GroupedOrderExecution"]:
        closing = GroupedOrderExecution(
            contract=self.contract,
            # -1 ms for the UI to sort it correctly
            time_completed=self.time_completed - timedelta(milliseconds=1),
            side=self.side,
            quantity=closing_qty,
            avg_price=self.avg_price,
            realized_pnl=self.realized_pnl,
        )
        opening = GroupedOrderExecution(
            contract=self.contract,
            time_completed=self.time_completed,
            side=self.side,
            quantity=self.quantity - closing_qty,
            avg_price=self.avg_price,
            realized_pnl=None,
        )

        return closing, opening


OrderExecutionGroupKey = tuple[int, ExecutionSideConst, int]


class OrderExecutionCollection:
    def _init_grouped_executions(self, order_execs: Iterable[OrderExecution]):
        grouped_executions: DefaultDict[OrderExecutionGroupKey, list[OrderExecution]] = defaultdict(list)
        for execution in order_execs:
            key = (
                execution.order_id,
                execution.side,
                get_contract_identifier(execution.contract),
            )
            grouped_executions[key].append(execution)

        # Do not activate the tracker for the 1st execution as it might start with existing position
        position_tracker: dict[int, Decimal] = {}
        for key, grouped in sorted(
                grouped_executions.items(),
                key=lambda item: min(execution.time for execution in item[1])
        ):
            _, _, contract_identifier = key

            grouped_execution = GroupedOrderExecution.from_executions(grouped)

            if grouped_execution.realized_pnl:
                if contract_identifier not in position_tracker:
                    # Activate tracker
                    position_tracker[contract_identifier] = Decimal(0)
                else:
                    position = position_tracker[contract_identifier]

                    # Position reduced or zero-ed
                    if position and grouped_execution.quantity > abs(position):
                        # Position reversed
                        closing, opening = grouped_execution.to_closing_and_opening(abs(position))

                        # --- Append closing execution
                        self._executions[contract_identifier].append(closing)
                        # --- Append opening (reversed) execution
                        self._executions[contract_identifier].append(opening)

                        position_tracker[contract_identifier] = position + grouped_execution.signed_quantity
                        continue

                    position_tracker[contract_identifier] += grouped_execution.signed_quantity
            elif contract_identifier in position_tracker:
                # Tracking positions
                position_tracker[contract_identifier] += grouped_execution.signed_quantity

            self._executions[contract_identifier].append(grouped_execution)

    @staticmethod
    def _init_exec_dataframe_single(
            grouped_executions: list[GroupedOrderExecution], multiplier: float
    ) -> DataFrame:
        df = DataFrame(grouped_executions)
        df.sort_values(by=[ExecutionDataCol.EPOCH_SEC], inplace=True)

        # Replace `None` with `NaN`
        df[ExecutionDataCol.REALIZED_PNL].replace([None], np.nan, inplace=True)

        # Profit / Loss / WR
        df[ExecutionDataCol.PROFIT] = (df[ExecutionDataCol.REALIZED_PNL] > 0).cumsum()
        df[ExecutionDataCol.LOSS] = (df[ExecutionDataCol.REALIZED_PNL] < 0).cumsum()
        df[ExecutionDataCol.WIN_RATE] = df[ExecutionDataCol.PROFIT].divide(
            df[ExecutionDataCol.PROFIT] + df[ExecutionDataCol.LOSS]
        )

        # Profit / Loss / WR (Long)
        df[ExecutionDataCol.PROFIT_ON_LONG] = (
                (df[ExecutionDataCol.REALIZED_PNL] > 0) & (df[ExecutionDataCol.SIDE] == "SLD")
        ).cumsum()
        df[ExecutionDataCol.LOSS_ON_LONG] = (
                (df[ExecutionDataCol.REALIZED_PNL] < 0) & (df[ExecutionDataCol.SIDE] == "SLD")
        ).cumsum()
        df[ExecutionDataCol.WIN_RATE_ON_LONG] = df[ExecutionDataCol.PROFIT_ON_LONG].divide(
            df[ExecutionDataCol.PROFIT_ON_LONG] + df[ExecutionDataCol.LOSS_ON_LONG]
        )

        # Profit / Loss / WR (Short)
        df[ExecutionDataCol.PROFIT_ON_SHORT] = (
                (df[ExecutionDataCol.REALIZED_PNL] > 0) & (df[ExecutionDataCol.SIDE] == "BOT")
        ).cumsum()
        df[ExecutionDataCol.LOSS_ON_SHORT] = (
                (df[ExecutionDataCol.REALIZED_PNL] < 0) & (df[ExecutionDataCol.SIDE] == "BOT")
        ).cumsum()
        df[ExecutionDataCol.WIN_RATE_ON_SHORT] = df[ExecutionDataCol.PROFIT_ON_SHORT].divide(
            df[ExecutionDataCol.PROFIT_ON_SHORT] + df[ExecutionDataCol.LOSS_ON_SHORT]
        )

        # Total Profit / Avg Profit
        df[ExecutionDataCol.TOTAL_PROFIT] = (
            df[df[ExecutionDataCol.REALIZED_PNL] > 0][ExecutionDataCol.REALIZED_PNL].cumsum()
        )
        df[ExecutionDataCol.TOTAL_PROFIT].fillna(0, inplace=True)
        df[ExecutionDataCol.AVG_PNL_PROFIT] = df[ExecutionDataCol.TOTAL_PROFIT] \
            .divide(df[ExecutionDataCol.PROFIT]) \
            .replace(0, np.nan) \
            .fillna(method="ffill")

        # Total Loss / Avg Loss
        df[ExecutionDataCol.TOTAL_LOSS] = (
            df[df[ExecutionDataCol.REALIZED_PNL] < 0][ExecutionDataCol.REALIZED_PNL].cumsum()
        )
        df[ExecutionDataCol.TOTAL_LOSS].fillna(0, inplace=True)
        df[ExecutionDataCol.AVG_PNL_LOSS] = df[ExecutionDataCol.TOTAL_LOSS] \
            .divide(df[ExecutionDataCol.LOSS]) \
            .replace(0, np.nan) \
            .fillna(method="ffill")

        # PnL RR ratio / EWR
        df[ExecutionDataCol.AVG_PNL_RR_RATIO] = abs(
            df[ExecutionDataCol.AVG_PNL_PROFIT].divide(df[ExecutionDataCol.AVG_PNL_LOSS])
        )
        df[ExecutionDataCol.AVG_PNL_EWR] = np.divide(
            1,
            1 + df[ExecutionDataCol.AVG_PNL_RR_RATIO],
        )

        # Total PnL
        df[ExecutionDataCol.REALIZED_PNL_SUM] = df[ExecutionDataCol.REALIZED_PNL].cumsum()

        # Px Side / Total Px Side
        df[ExecutionDataCol.PX_SIDE] = (
                df[ExecutionDataCol.REALIZED_PNL].divide(df[ExecutionDataCol.QUANTITY].astype(float)) / multiplier
        )
        df[ExecutionDataCol.PX_SIDE_SUM] = df[ExecutionDataCol.PX_SIDE].cumsum()

        # Total Px+ / Avg Px+
        df[ExecutionDataCol.TOTAL_PX_PROFIT] = (
            df[df[ExecutionDataCol.PX_SIDE] > 0][ExecutionDataCol.PX_SIDE].cumsum()
        )
        df[ExecutionDataCol.TOTAL_PX_PROFIT].fillna(0, inplace=True)
        df[ExecutionDataCol.AVG_PX_PROFIT] = df[ExecutionDataCol.TOTAL_PX_PROFIT] \
            .divide(df[ExecutionDataCol.PROFIT]) \
            .replace(0, np.nan) \
            .fillna(method="ffill")

        # Total Px- / Avg Px-
        df[ExecutionDataCol.TOTAL_PX_LOSS] = (
            df[df[ExecutionDataCol.PX_SIDE] < 0][ExecutionDataCol.PX_SIDE].cumsum()
        )
        df[ExecutionDataCol.TOTAL_PX_LOSS].fillna(0, inplace=True)
        df[ExecutionDataCol.AVG_PX_LOSS] = df[ExecutionDataCol.TOTAL_PX_LOSS] \
            .divide(df[ExecutionDataCol.LOSS]) \
            .replace(0, np.nan) \
            .fillna(method="ffill")

        # Px RR / EWR
        df[ExecutionDataCol.AVG_PX_RR_RATIO] = abs(
            df[ExecutionDataCol.AVG_PX_PROFIT].divide(df[ExecutionDataCol.AVG_PX_LOSS])
        )
        df[ExecutionDataCol.AVG_PX_EWR] = np.divide(
            1,
            1 + df[ExecutionDataCol.AVG_PX_RR_RATIO],
        )

        # Remove NaNs
        df.fillna(np.nan, inplace=True)
        df.replace([np.nan, np.inf, -np.inf], None, inplace=True)

        return df

    def _init_exec_dataframe(self):
        for identifier, grouped_executions in self._executions.items():
            self._executions_dataframe[identifier] = self._init_exec_dataframe_single(
                grouped_executions,
                multiplier=float(grouped_executions[0].contract.multiplier),
            )

    def __init__(self, order_execs: Iterable[OrderExecution]):
        self._executions: DefaultDict[int, list[GroupedOrderExecution]] = defaultdict(list)
        self._init_grouped_executions(order_execs)

        self._executions_dataframe: dict[int, DataFrame] = {}
        self._init_exec_dataframe()

    def print_executions(self):
        for executions in self._executions.values():
            for execution in executions:
                print(
                    execution.contract.localSymbol, execution.time_completed, execution.avg_price,
                    execution.quantity, execution.realized_pnl
                )

    @property
    def executions(self) -> dict[int, list[GroupedOrderExecution]]:
        return self._executions

    @property
    def execution_dataframes(self) -> dict[int, DataFrame]:
        return self._executions_dataframe
