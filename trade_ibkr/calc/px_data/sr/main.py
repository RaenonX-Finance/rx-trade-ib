import numpy as np
from pandas import DataFrame

from trade_ibkr.const import SR_METHOD, SR_MULTIPLIER, SR_PERIOD
from trade_ibkr.enums import PxDataCol
from .fx import support_resistance_extrema, support_resistance_fractal, support_resistance_window
from .model import SRLevelsData


def calc_support_resistance_levels(df: DataFrame) -> SRLevelsData:
    min_gap = np.mean(df[PxDataCol.DIFF_SMA].tail(SR_PERIOD)) * SR_MULTIPLIER

    levels_fractal = support_resistance_fractal(df, min_gap) if SR_METHOD["fractal"] else []
    levels_window = support_resistance_window(df, min_gap) if SR_METHOD["window"] else []
    levels_extrema = support_resistance_extrema(df, min_gap) if SR_METHOD["extrema"] else []

    return SRLevelsData(
        levels={
            "fractal": levels_fractal,
            "window": levels_window,
            "extrema": levels_extrema,
        },
        min_gap=min_gap,
        df=df
    )
