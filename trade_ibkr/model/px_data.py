from collections import Counter
from datetime import datetime, timedelta
from typing import Generator, TYPE_CHECKING

import numpy as np
import pandas as pd
import talib
from ibapi.contract import ContractDetails
from pandas import DataFrame, DatetimeIndex, Series, to_datetime
from scipy.signal import argrelextrema

from trade_ibkr.calc import calc_support_resistance_levels
from trade_ibkr.const import console
from trade_ibkr.enums import CandlePos, PxDataCol
from trade_ibkr.utils import closest_diff

if TYPE_CHECKING:
    from trade_ibkr.model import BarDataDict


class PxData:
    def _proc_df(self):
        self.dataframe[PxDataCol.DATE] = to_datetime(
            self.dataframe[PxDataCol.EPOCH_SEC], utc=True, unit="s"
        ).dt.tz_convert("America/Chicago").dt.tz_localize(None)
        self.dataframe.set_index(DatetimeIndex(self.dataframe[PxDataCol.DATE]), inplace=True)

        self.dataframe[PxDataCol.DATE_MARKET] = to_datetime(np.where(
            self.dataframe[PxDataCol.DATE].dt.hour < 17,
            self.dataframe[PxDataCol.DATE].dt.date,
            self.dataframe[PxDataCol.DATE].dt.date + timedelta(days=1)
        ))

        self.dataframe[PxDataCol.AMPLITUDE_HL] = talib.EMA(
            abs(self.dataframe[PxDataCol.HIGH] - self.dataframe[PxDataCol.LOW]),
            timeperiod=10
        )
        self.dataframe[PxDataCol.AMPLITUDE_OC] = talib.EMA(
            abs(self.dataframe[PxDataCol.OPEN] - self.dataframe[PxDataCol.CLOSE]),
            timeperiod=10
        )

        self.dataframe[PxDataCol.LOCAL_MIN] = self.dataframe.iloc[
            argrelextrema(self.dataframe[PxDataCol.LOW].values, np.less_equal, order=7)[0]
        ][PxDataCol.LOW]
        self.dataframe[PxDataCol.LOCAL_MAX] = self.dataframe.iloc[
            argrelextrema(self.dataframe[PxDataCol.HIGH].values, np.greater_equal, order=7)[0]
        ][PxDataCol.HIGH]

        self.dataframe[PxDataCol.PRICE_TIMES_VOLUME] = np.multiply(
            self.dataframe[PxDataCol.CLOSE],
            self.dataframe[PxDataCol.VOLUME]
        )
        mkt_data_group = self.dataframe.groupby(PxDataCol.DATE_MARKET)
        self.dataframe[PxDataCol.VWAP] = np.divide(
            mkt_data_group[PxDataCol.PRICE_TIMES_VOLUME].transform(pd.Series.cumsum),
            mkt_data_group[PxDataCol.VOLUME].transform(pd.Series.cumsum),
        )

        # Remove NaNs
        self.dataframe = self.dataframe.fillna(np.nan).replace([np.nan], [None])

    def __init__(
            self, *,
            contract: ContractDetails,
            bars: list["BarDataDict"] | None = None,
            dataframe: DataFrame | None = None
    ):
        self.contract: ContractDetails = contract
        self.dataframe: DataFrame = DataFrame(bars) if bars else dataframe

        if self.dataframe is None:
            raise ValueError("Must specify either `bars` or `dataframe` for PxData")

        self._proc_df()

        self.sr_levels_data = calc_support_resistance_levels(self.dataframe)

    def get_px_sr_score(self, px: float) -> float:
        if not self.sr_levels_data.levels["window"] or not self.sr_levels_data.levels["fractal"]:
            return float("NaN")

        fractal = closest_diff(self.sr_levels_data.levels["fractal"], px) / self.get_current()[PxDataCol.CLOSE]
        window = closest_diff(self.sr_levels_data.levels["window"], px) / self.get_current()[PxDataCol.CLOSE]

        return fractal * window * 1E8

    def get_current(self) -> Series:
        return self.dataframe.iloc[-1]

    def get_last_n(self, n: int) -> Series:
        return self.dataframe.iloc[-n]

    @staticmethod
    def _get_series_at(original: Series, candle_pos: CandlePos) -> Series:
        series = original.copy()

        match candle_pos:
            case CandlePos.OPEN:
                series[PxDataCol.HIGH] = original[PxDataCol.OPEN]
                series[PxDataCol.LOW] = original[PxDataCol.OPEN]
                series[PxDataCol.CLOSE] = original[PxDataCol.OPEN]
            case CandlePos.HIGH:
                series[PxDataCol.CLOSE] = original[PxDataCol.HIGH]
            case CandlePos.LOW:
                series[PxDataCol.CLOSE] = original[PxDataCol.LOW]
            case CandlePos.CLOSE:
                pass

        return series

    def get_dataframes_backtest(self, *, min_data_rows: int) -> Generator[tuple[DataFrame, bool], None, None]:
        """Returns (price data, is new px data)."""
        for row_count in range(min_data_rows, len(self.dataframe.index)):
            sub_df: DataFrame = self.dataframe.iloc[:row_count]

            sub_df_modified = sub_df.copy()

            for idx, pos in enumerate((CandlePos.OPEN, CandlePos.HIGH, CandlePos.LOW, CandlePos.CLOSE)):
                sub_df_modified.iloc[-1] = self._get_series_at(sub_df.iloc[-1], pos)
                yield sub_df_modified, idx == 0

    def print_current_sr_level_position(self):
        current_datetime = datetime.now().strftime("%H:%M:%S")
        current_close = self.get_current()[PxDataCol.CLOSE]

        sr_levels = Counter(self.sr_levels_data.levels["window"] + self.sr_levels_data.levels["fractal"])
        sr_level_txt = " / ".join(f"{key}{' !' if sr_levels[key] > 1 else ''}" for key in sorted(sr_levels.keys()))

        console.print(current_datetime)
        console.print(
            f"{current_close:9.2f} | "
            # f"{executions_df.side:12} | "
            # f"{executions_df.avg_px:9.2f} | "
            # f"{px_diff:9.2f} | "
            f"\n{sr_level_txt}",
        )

    @property
    def earliest_time(self) -> datetime:
        return self.dataframe[PxDataCol.DATE].min()

    @property
    def current_close(self) -> float:
        return self.dataframe.iloc[-1][PxDataCol.CLOSE]
