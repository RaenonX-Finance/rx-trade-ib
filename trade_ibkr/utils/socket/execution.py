import json
from typing import TYPE_CHECKING, TypeAlias, TypedDict

from pandas import DataFrame

from trade_ibkr.enums import ExecutionDataCol, OrderSideConst

if TYPE_CHECKING:
    from trade_ibkr.model import OrderExecutionCollection


class ExecutionGroup(TypedDict):
    epochSec: float
    side: OrderSideConst
    quantity: float
    avgPx: float

    realizedPnL: float | None

    profit: float | None
    loss: float | None
    winRate: float | None

    avgTotalProfit: float | None
    avgTotalLoss: float | None
    avgTotalRrRatio: float | None
    thresholdWinRate: float | None

    totalPnL: float | None


ExecutionDict: TypeAlias = dict[int, list[ExecutionGroup]]


def _from_grouped_execution_dataframe(executions_df: DataFrame) -> list[ExecutionGroup]:
    return [
        {
            "epochSec": row[ExecutionDataCol.EPOCH_SEC],
            "side": row[ExecutionDataCol.SIDE],
            "quantity": float(row[ExecutionDataCol.QUANTITY]),
            "avgPx": row[ExecutionDataCol.AVG_PX],
            "realizedPnL": row[ExecutionDataCol.REALIZED_PNL],
            "profit": row[ExecutionDataCol.PROFIT],
            "loss": row[ExecutionDataCol.LOSS],
            "winRate": row[ExecutionDataCol.WIN_RATE],
            "avgTotalProfit": row[ExecutionDataCol.AVG_TOTAL_PROFIT],
            "avgTotalLoss": row[ExecutionDataCol.AVG_TOTAL_LOSS],
            "avgTotalRrRatio": row[ExecutionDataCol.AVG_TOTAL_RR_RATIO],
            "thresholdWinRate": row[ExecutionDataCol.THRESHOLD_WIN_RATE],
            "totalPnL": row[ExecutionDataCol.TOTAL_PNL],
        } for _, row in executions_df.iterrows()
    ]


def to_socket_message_execution(execution: "OrderExecutionCollection") -> str:
    data: ExecutionDict = {
        contract_identifier: _from_grouped_execution_dataframe(exec_df)
        for contract_identifier, exec_df in execution.execution_dataframes.items()
    }

    return json.dumps(data)
