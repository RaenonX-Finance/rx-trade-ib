from typing import cast

import numpy as np
from pandas import DataFrame

from trade_ibkr.const import AVG_MULTIPLIER
from trade_ibkr.enums import PxDataCol
from .fx import support_resistance_fractal, support_resistance_window
from .model import SRLevelsData


def calc_support_resistance_levels(df: DataFrame) -> SRLevelsData:
    avg = cast(float, np.mean(df[PxDataCol.HIGH] - df[PxDataCol.LOW]) * AVG_MULTIPLIER)

    levels_fractal = support_resistance_fractal(df, avg)
    levels_window = support_resistance_window(df, avg)

    return SRLevelsData(levels={"fractal": levels_fractal, "window": levels_window}, bar_hl_avg=avg, df=df)
