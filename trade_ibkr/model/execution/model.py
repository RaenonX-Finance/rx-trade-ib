from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
from ibapi.contract import Contract

from trade_ibkr.enums import ExecutionSideConst


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

    def to_closing_and_opening(
            self, closing_qty: Decimal
    ) -> tuple["GroupedOrderExecution", "GroupedOrderExecution"]:
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
