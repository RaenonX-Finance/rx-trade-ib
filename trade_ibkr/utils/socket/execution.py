import json
from typing import TYPE_CHECKING, TypeAlias, TypedDict

from trade_ibkr.enums import OrderSideConst

if TYPE_CHECKING:
    from trade_ibkr.model import GroupedOrderExecution, OrderExecutionCollection


class ExecutionGroup(TypedDict):
    epochSec: float
    side: OrderSideConst
    quantity: float
    avgPx: float
    realizedPnL: float | None


ExecutionDict: TypeAlias = dict[int, list[ExecutionGroup]]


def _from_grouped_executions(executions: list["GroupedOrderExecution"]) -> list[ExecutionGroup]:
    return [
        {
            "epochSec": execution.epoch_sec,
            "side": execution.side,
            "quantity": float(execution.quantity),
            "avgPx": execution.avg_price,
            "realizedPnL": execution.realized_pnl,
        } for execution in executions
    ]


def to_socket_message_execution(execution: "OrderExecutionCollection") -> str:
    data: ExecutionDict = {
        contract_identifier: _from_grouped_executions(grouped_executions)
        for contract_identifier, grouped_executions in execution.executions.items()
    }

    return json.dumps(data)
