from pandas import DataFrame

from trade_ibkr.enums import PxDataCol
from .fx import support_resistance_extrema
from .model import SRLevelsData


def calc_support_resistance_levels(df: DataFrame) -> SRLevelsData:
    return SRLevelsData(
        levels=support_resistance_extrema(df),
        min_gap=df[PxDataCol.DIFF_SMA].mean()
    )
