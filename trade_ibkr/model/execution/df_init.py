from typing import TYPE_CHECKING

import numpy as np
from pandas import DataFrame

from trade_ibkr.enums import ExecutionDataCol, PxDataCol
from .model import GroupedOrderExecution

if TYPE_CHECKING:
    from trade_ibkr.model import PxData


def _profit_loss(df: DataFrame):
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


def _summary(df: DataFrame, multiplier: float, px_data: "PxData"):
    # Total PnL
    df[ExecutionDataCol.REALIZED_PNL_SUM] = df[ExecutionDataCol.REALIZED_PNL].cumsum()

    # Px Side / Total Px Side
    df[ExecutionDataCol.PX_SIDE] = (
            df[ExecutionDataCol.REALIZED_PNL].divide(df[ExecutionDataCol.QUANTITY].astype(float)) / multiplier
    )
    df[ExecutionDataCol.PX_SIDE_SUM] = df[ExecutionDataCol.PX_SIDE].cumsum()

    # Px Side Amplitude Ratio
    df_temp = df.copy()
    df_temp[ExecutionDataCol.TIME_COMPLETED] = df_temp[ExecutionDataCol.TIME_COMPLETED] \
        .dt \
        .floor(f"{px_data.period_sec}S")
    df_temp = df_temp.merge(
        px_data.dataframe,
        how="left", left_on=ExecutionDataCol.TIME_COMPLETED, right_index=True
    )
    df_temp[PxDataCol.DIFF_SMA].replace([None], np.nan, inplace=True)
    df[ExecutionDataCol.PX_SIDE_DIFF_SMA_RATIO] = abs(
        df_temp[ExecutionDataCol.PX_SIDE].divide(df_temp[PxDataCol.DIFF_SMA])
    )


def _analysis_pnl(df: DataFrame):
    # Total Profit / Avg Profit
    df[ExecutionDataCol.TOTAL_PROFIT] = (
        df[df[ExecutionDataCol.REALIZED_PNL] > 0][ExecutionDataCol.REALIZED_PNL].cumsum()
    )
    df[ExecutionDataCol.TOTAL_PROFIT].fillna(method="ffill", inplace=True)
    df[ExecutionDataCol.AVG_PNL_PROFIT] = df[ExecutionDataCol.TOTAL_PROFIT] \
        .divide(df[ExecutionDataCol.PROFIT]) \
        .replace(0, np.nan) \
        .fillna(method="ffill")

    # Total Loss / Avg Loss
    df[ExecutionDataCol.TOTAL_LOSS] = (
        df[df[ExecutionDataCol.REALIZED_PNL] < 0][ExecutionDataCol.REALIZED_PNL].cumsum()
    )
    df[ExecutionDataCol.TOTAL_LOSS].fillna(method="ffill", inplace=True)
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


def _analysis_px_side(df: DataFrame):
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


def init_exec_dataframe(
        grouped_executions: list[GroupedOrderExecution],
        *, multiplier: float, px_data: "PxData"
) -> DataFrame:
    df = DataFrame(grouped_executions)
    df.sort_values(by=[ExecutionDataCol.EPOCH_SEC], inplace=True)

    # Replace `None` with `NaN`
    df[ExecutionDataCol.REALIZED_PNL].replace([None], np.nan, inplace=True)

    _profit_loss(df)
    _summary(df, multiplier, px_data)
    _analysis_pnl(df)
    _analysis_px_side(df)

    # Remove NaNs
    df.fillna(np.nan, inplace=True)
    df.replace([np.nan, np.inf, -np.inf], None, inplace=True)

    return df
