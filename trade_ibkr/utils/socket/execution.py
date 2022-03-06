import json
from typing import TYPE_CHECKING, TypeAlias, TypedDict

from pandas import DataFrame

from trade_ibkr.enums import ExecutionDataCol, OrderSideConst
from .utils import df_rows_to_list_of_data

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
    pxSideAmplRatio: float | None

    avgPxProfit: float | None
    avgPxLoss: float | None
    avgPxRrRatio: float | None
    avgPxEwr: float | None


ExecutionDict: TypeAlias = dict[int, list[ExecutionGroup]]


def _from_grouped_execution_dataframe(executions_df: DataFrame) -> list[ExecutionGroup]:
    df = executions_df.copy()
    df[ExecutionDataCol.QUANTITY] = df[ExecutionDataCol.QUANTITY].astype(float)

    columns = {
        ExecutionDataCol.EPOCH_SEC: "epochSec",
        ExecutionDataCol.SIDE: "side",
        ExecutionDataCol.QUANTITY: "quantity",
        ExecutionDataCol.AVG_PX: "avgPx",
        ExecutionDataCol.REALIZED_PNL: "realizedPnL",
        ExecutionDataCol.REALIZED_PNL_SUM: "realizedPnLSum",
        ExecutionDataCol.PROFIT: "profit",
        ExecutionDataCol.LOSS: "loss",
        ExecutionDataCol.WIN_RATE: "winRate",
        ExecutionDataCol.PROFIT_ON_LONG: "profitLong",
        ExecutionDataCol.LOSS_ON_LONG: "lossLong",
        ExecutionDataCol.WIN_RATE_ON_LONG: "winRateLong",
        ExecutionDataCol.PROFIT_ON_SHORT: "profitShort",
        ExecutionDataCol.LOSS_ON_SHORT: "lossShort",
        ExecutionDataCol.WIN_RATE_ON_SHORT: "winRateShort",
        ExecutionDataCol.AVG_PNL_PROFIT: "avgPnLProfit",
        ExecutionDataCol.AVG_PNL_LOSS: "avgPnLLoss",
        ExecutionDataCol.AVG_PNL_RR_RATIO: "avgPnLRrRatio",
        ExecutionDataCol.AVG_PNL_EWR: "avgPnLEwr",
        ExecutionDataCol.PX_SIDE: "pxSide",
        ExecutionDataCol.PX_SIDE_SUM: "pxSideSum",
        ExecutionDataCol.PX_SIDE_AMPL_RATIO: "pxSideAmplRatio",
        ExecutionDataCol.AVG_PX_PROFIT: "avgPxProfit",
        ExecutionDataCol.AVG_PX_LOSS: "avgPxLoss",
        ExecutionDataCol.AVG_PX_RR_RATIO: "avgPxRrRatio",
        ExecutionDataCol.AVG_PX_EWR: "avgPxEwr",
    }

    return df_rows_to_list_of_data(df, columns)


def to_socket_message_execution(execution: "OrderExecutionCollection") -> str:
    data: ExecutionDict = {
        contract_identifier: _from_grouped_execution_dataframe(exec_df)
        for contract_identifier, exec_df in execution.execution_dataframes.items()
    }

    return json.dumps(data)
