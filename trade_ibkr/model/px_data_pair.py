from typing import TYPE_CHECKING

import pandas as pd
import talib
from pandas import DataFrame, DatetimeIndex, Series, to_datetime
from talib import MA_Type

from trade_ibkr.enums import PxDataCol, PxDataPairCol, PxDataPairSuffix

if TYPE_CHECKING:
    from trade_ibkr.model import BarDataDict, GetSpread


class PxDataPair:
    @staticmethod
    def _proc_df(df: DataFrame):
        df[PxDataCol.DATE] = to_datetime(
            df[PxDataCol.EPOCH_SEC], utc=True, unit="s"
        ).dt.tz_convert("America/Chicago").dt.tz_localize(None)
        df.set_index(DatetimeIndex(df[PxDataCol.DATE]), inplace=True)

    def _get_merged_df(self, get_spread: "GetSpread") -> DataFrame:
        df = pd.merge(
            self.dataframe_on_low, self.dataframe_on_hi,
            on=PxDataCol.DATE, suffixes=(PxDataPairSuffix.ON_HI, PxDataPairSuffix.ON_LO)
        )
        df.index = pd.to_datetime(df[PxDataPairCol.DATE])
        df.drop(columns=[PxDataPairCol.DATE], inplace=True)

        df[PxDataPairCol.SPREAD] = get_spread(df[PxDataPairCol.CLOSE_HI], df[PxDataPairCol.CLOSE_LO])
        upper, mid, lower = talib.BBANDS(
            df[PxDataPairCol.SPREAD], timeperiod=10, nbdevup=2, nbdevdn=2, matype=MA_Type.SMA
        )
        df[PxDataPairCol.SPREAD_HI] = upper
        df[PxDataPairCol.SPREAD_MID] = mid
        df[PxDataPairCol.SPREAD_LO] = lower

        return df

    def __init__(
            self, *,
            bars_on_low: list["BarDataDict"],
            bars_on_hi: list["BarDataDict"],
            get_spread: "GetSpread",
    ):
        self.dataframe_on_low: DataFrame = DataFrame(bars_on_low)
        self._proc_df(self.dataframe_on_low)

        self.dataframe_on_hi: DataFrame = DataFrame(bars_on_hi)
        self._proc_df(self.dataframe_on_hi)

        self.dataframe_merged = self._get_merged_df(get_spread)

    def get_last(self) -> Series:
        return self.dataframe_merged.iloc[-1]
