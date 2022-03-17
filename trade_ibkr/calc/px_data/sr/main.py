import numpy as np
from pandas import DataFrame

from trade_ibkr.const import SR_MULTIPLIER, SR_PERIOD
from trade_ibkr.enums import PxDataCol
from .fx import support_resistance_extrema
from .model import SRLevelsData


def calc_support_resistance_levels(df: DataFrame) -> SRLevelsData:
    min_gap = np.mean(df[PxDataCol.DIFF_SMA].tail(SR_PERIOD)) * SR_MULTIPLIER

    return SRLevelsData(
        levels=support_resistance_extrema(df),
        min_gap=min_gap,
        df=df
    )
