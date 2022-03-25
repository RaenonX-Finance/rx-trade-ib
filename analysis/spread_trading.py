from dataclasses import dataclass
from datetime import time

import numpy as np
import pandas as pd
import plotly.express as px
import talib
from pandas import DataFrame
from talib import MA_Type

from trade_ibkr.utils import print_log


@dataclass(kw_only=True)
class SpreadTradingCommodity:
    file_path: str
    name: str
    lot: int
    multiplier: float

    def get_weighted_px(self, px: float) -> float:
        return self.lot * self.multiplier * px


@dataclass(kw_only=True)
class SpreadTradingParams:
    data_1: SpreadTradingCommodity
    data_2: SpreadTradingCommodity

    time_start: str
    time_end: str

    commission_single: float
    div_reverse: bool


def get_data_df(params: SpreadTradingParams) -> DataFrame:
    df_1 = pd.read_csv(params.data_1.file_path)
    df_1 = df_1[["date", "close"]]
    df_2 = pd.read_csv(params.data_2.file_path)
    df_2 = df_2[["date", "close"]]

    df = pd.merge(df_1, df_2, on="date", suffixes=(f"_{params.data_1.name}", f"_{params.data_2.name}"))
    df.index = pd.to_datetime(df["date"])
    df.drop(columns=["date"], inplace=True)
    return df


def attach_data_to_df(df: DataFrame, params: SpreadTradingParams) -> None:
    if params.div_reverse:
        df["px_diff"] = np.log(df[f"close_{params.data_2.name}"].divide(df[f"close_{params.data_1.name}"]))
    else:
        df["px_diff"] = np.log(df[f"close_{params.data_1.name}"].divide(df[f"close_{params.data_2.name}"]))
    upper, mid, lower = talib.BBANDS(df["px_diff"], timeperiod=10, nbdevup=2, nbdevdn=2, matype=MA_Type.SMA)
    df["px_diff_upper"] = upper
    df["px_diff_mid"] = mid
    df["px_diff_lower"] = lower


def get_df_between_time(df: DataFrame, params: SpreadTradingParams) -> DataFrame:
    return df.between_time(params.time_start, params.time_end)


def apply_strategy(df: DataFrame, params: SpreadTradingParams) -> DataFrame:
    print_log(
        f"Data 1: {params.data_1.name} / Data 2: {params.data_2.name}\n"
        f"Weighted Px 1: {params.data_1.get_weighted_px(df[f'close_{params.data_1.name}'][-1]):.2f}\n"
        f"Weighted Px 2: {params.data_2.get_weighted_px(df[f'close_{params.data_2.name}'][-1]):.2f}"
    )

    if df["px_diff"][-1] < 0:
        print_log("Px diff value is negative, the division order should be reversed!")

    name_1 = params.data_1.name
    name_2 = params.data_2.name

    executions = []
    current_pnl = 0

    for dt, row in df.iterrows():
        last = executions[-1] if executions else None

        # Exit - no cross-day position
        # noinspection PyUnresolvedReferences
        if dt.time() == time(6, 30) and last["position"] == "open":
            executions[-1] |= {
                f"exit_{name_1}": row[f"close_{name_1}"],
                f"exit_{name_2}": row[f"close_{name_2}"],
                "exit_t": dt,
                "position": "close",
            }
            continue

        msg = f"{current_pnl} {last['position']}" if last else ""
        msg += f" {dt}"
        print_log(msg)

        # Entry - out of band
        if not last or last["position"] == "close":
            if row["px_diff"] > row["px_diff_upper"]:
                executions.append({
                    "buy": name_2,
                    "sell": name_1,
                    "entry_t": dt,
                    f"entry_{name_1}": row[f"close_{name_1}"],
                    f"entry_{name_2}": row[f"close_{name_2}"],
                    f"exit_{name_1}": None,
                    f"exit_{name_2}": None,
                    "exit_t": None,
                    "position": "open",
                    "pnl_highest": 0,
                    "pnl_lowest": 0,
                })

            if row["px_diff"] < row["px_diff_lower"]:
                executions.append({
                    "buy": name_1,
                    "sell": name_2,
                    "entry_t": dt,
                    f"entry_{name_1}": row[f"close_{name_1}"],
                    f"entry_{name_2}": row[f"close_{name_2}"],
                    f"exit_{name_1}": None,
                    f"exit_{name_2}": None,
                    "exit_t": None,
                    "position": "open",
                    "pnl_highest": 0,
                    "pnl_lowest": 0,
                })

            continue
        # Take profit - back to MID
        elif (
                (last["buy"] == name_1 and row["px_diff"] < row["px_diff_mid"]) or
                (last["buy"] == name_2 and row["px_diff"] > row["px_diff_mid"])
        ):
            executions[-1] |= {
                f"exit_{name_1}": row[f"close_{name_1}"],
                f"exit_{name_2}": row[f"close_{name_2}"],
                "exit_t": dt,
                "position": "close",
            }
            current_pnl = 0

        # Record PnL
        if last["position"] == "open":
            pnl_1 = (
                    (row[f"close_{name_1}"] - last[f"entry_{name_1}"]) *
                    (1 if last["buy"] == name_1 else -1)
                    * params.data_1.lot * params.data_1.multiplier
            )
            pnl_2 = (
                    (row[f"close_{name_2}"] - last[f"entry_{name_2}"])
                    * (1 if last["buy"] == name_2 else -1)
                    * params.data_2.lot * params.data_2.multiplier
            )

            current_pnl = pnl_1 + pnl_2

            executions[-1] |= {
                "pnl_highest": max(last["pnl_highest"], current_pnl),
                "pnl_lowest": min(last["pnl_lowest"], current_pnl),
            }

        # Take profit - lock profit
        if current_pnl < 10 and last["pnl_highest"] > 40:
            executions[-1] |= {
                f"exit_{name_1}": row[f"close_{name_1}"],
                f"exit_{name_2}": row[f"close_{name_2}"],
                "exit_t": dt,
                "position": "close",
            }

        # Stop loss - force close
        if current_pnl < -50:
            executions[-1] |= {
                f"exit_{name_1}": row[f"close_{name_1}"],
                f"exit_{name_2}": row[f"close_{name_2}"],
                "exit_t": dt,
                "position": "close",
            }

    df_exec = DataFrame(executions)
    df_exec["hold_period"] = df_exec["exit_t"] - df_exec["entry_t"]
    df_exec[f"px_side_{name_1}"] = (
            (df_exec[f"exit_{name_1}"] - df_exec[f"entry_{name_1}"])
            * np.where(df_exec["buy"] == name_1, 1, -1)
    )
    df_exec[f"px_side_{name_2}"] = (
            (df_exec[f"exit_{name_2}"] - df_exec[f"entry_{name_2}"])
            * np.where(df_exec["buy"] == name_2, 1, -1)
    )
    df_exec[f"pnl_{name_1}"] = df_exec[f"px_side_{name_1}"] * params.data_1.lot * params.data_1.multiplier
    df_exec[f"pnl_{name_2}"] = df_exec[f"px_side_{name_2}"] * params.data_2.lot * params.data_2.multiplier
    df_exec["pnl_single"] = (
            df_exec[f"pnl_{name_1}"]
            + df_exec[f"pnl_{name_2}"]
            - params.commission_single
            * (params.data_1.lot + params.data_2.lot)
    )
    df_exec["pnl_cum"] = df_exec["pnl_single"].cumsum()

    return df_exec


def show_pnl_plot(df_exec: DataFrame, params: SpreadTradingParams):
    fig = px.line(df_exec, x=df_exec.index, y="pnl_cum", title=f"{params.data_1.name} / {params.data_2.name}")
    fig.show()


def all_in_one(params: SpreadTradingParams):
    df = get_data_df(params)
    attach_data_to_df(df, params)
    df_selected = get_df_between_time(df, params)
    df_exec = apply_strategy(df_selected, params)
    show_pnl_plot(df_exec, params)


if __name__ == '__main__':
    # Margin as of 2022/03/08
    # MYM Intraday Initial: 1063
    # MES Intraday Initial: 1611
    # MNQ Intraday Initial: 2153

    all_in_one(SpreadTradingParams(
        data_1=SpreadTradingCommodity(
            file_path="../archive/futures/YM/20220222-20220307-1.csv",
            name="YM",
            lot=6,
            multiplier=0.5,
        ),
        data_2=SpreadTradingCommodity(
            file_path="../archive/futures/NQ/20220222-20220307-1.csv",
            name="NQ",
            lot=2,
            multiplier=2,
        ),
        time_start="02:30",
        time_end="06:30",
        commission_single=0.52,
        div_reverse=False,
    ))
