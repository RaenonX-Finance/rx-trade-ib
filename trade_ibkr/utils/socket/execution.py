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
    realizedPnLSum: float | None

    profit: float | None
    loss: float | None
    winRate: float | None

    profitLong: float | None
    lossLong: float | None
    winRateLong: float | None

    profitShort: float | None
    lossShort: float | None
    winRateShort: float | None

    avgPnLProfit: float | None
    avgPnLLoss: float | None
    avgPnLRrRatio: float | None
    avgPnLEwr: float | None

    pxSide: float | None
    pxSideSum: float | None

    avgPxProfit: float | None
    avgPxLoss: float | None
    avgPxRrRatio: float | None
    avgPxEwr: float | None


ExecutionDict: TypeAlias = dict[int, list[ExecutionGroup]]


def _from_grouped_execution_dataframe(executions_df: DataFrame) -> list[ExecutionGroup]:
    return [
        {
            "epochSec": row[ExecutionDataCol.EPOCH_SEC],
            "side": row[ExecutionDataCol.SIDE],
            "quantity": float(row[ExecutionDataCol.QUANTITY]),
            "avgPx": row[ExecutionDataCol.AVG_PX],
            "realizedPnL": row[ExecutionDataCol.REALIZED_PNL],
            "realizedPnLSum": row[ExecutionDataCol.REALIZED_PNL_SUM],
            "profit": row[ExecutionDataCol.PROFIT],
            "loss": row[ExecutionDataCol.LOSS],
            "winRate": row[ExecutionDataCol.WIN_RATE],
            "profitLong": row[ExecutionDataCol.PROFIT_ON_LONG],
            "lossLong": row[ExecutionDataCol.LOSS_ON_LONG],
            "winRateLong": row[ExecutionDataCol.WIN_RATE_ON_LONG],
            "profitShort": row[ExecutionDataCol.PROFIT_ON_SHORT],
            "lossShort": row[ExecutionDataCol.LOSS_ON_SHORT],
            "winRateShort": row[ExecutionDataCol.WIN_RATE_ON_SHORT],
            "avgPnLProfit": row[ExecutionDataCol.AVG_PNL_PROFIT],
            "avgPnLLoss": row[ExecutionDataCol.AVG_PNL_LOSS],
            "avgPnLRrRatio": row[ExecutionDataCol.AVG_PNL_RR_RATIO],
            "avgPnLEwr": row[ExecutionDataCol.AVG_PNL_EWR],
            "pxSide": row[ExecutionDataCol.PX_SIDE],
            "pxSideSum": row[ExecutionDataCol.PX_SIDE_SUM],
            "avgPxProfit": row[ExecutionDataCol.AVG_PX_PROFIT],
            "avgPxLoss": row[ExecutionDataCol.AVG_PX_LOSS],
            "avgPxRrRatio": row[ExecutionDataCol.AVG_PX_RR_RATIO],
            "avgPxEwr": row[ExecutionDataCol.AVG_PX_EWR],
        } for _, row in executions_df.iterrows()
    ]


def to_socket_message_execution(execution: "OrderExecutionCollection") -> str:
    data: ExecutionDict = {
        contract_identifier: _from_grouped_execution_dataframe(exec_df)
        for contract_identifier, exec_df in execution.execution_dataframes.items()
    }

    return json.dumps(data)
