import numpy as np
from pandas import DataFrame

from trade_ibkr.const import SR_MULTIPLIER, SR_PERIOD
from trade_ibkr.enums import PxDataCol
from .fx import support_resistance_fractal, support_resistance_window
from .model import SRLevelsData


def calc_support_resistance_levels(df: DataFrame) -> SRLevelsData:
    min_gap = np.mean(df[PxDataCol.HIGH].tail(SR_PERIOD) - df[PxDataCol.LOW].tail(SR_PERIOD)) * SR_MULTIPLIER

    levels_fractal = support_resistance_fractal(df, min_gap)
    levels_window = support_resistance_window(df, min_gap)

    return SRLevelsData(levels={"fractal": levels_fractal, "window": levels_window}, min_gap=min_gap, df=df)
