from dataclasses import dataclass, field
from decimal import Decimal

import numpy as np
from pandas import DataFrame

from trade_ibkr.enums import OrderSide


@dataclass(kw_only=True)
class BacktestOrderEntry:
    side: OrderSide
    quantity: Decimal
    px: float

    side_mult: float = field(init=False)  # For dataframe construction

    def __post_init__(self):
        self.side_mult = self.side.multiplier


class Orders:
    def __init__(self, multiplier: float, orders: list[BacktestOrderEntry]):
        df = DataFrame(orders)

        df["quantity"] = df["quantity"].astype(float)
        df["position"] = (df["quantity"] * df["side_mult"]).cumsum()
        df["px side"] = np.where(
            df["position"].shift(1) == 0,
            0,
            (df["px"] - df["px"].shift(1)) * df["side_mult"].shift(1)
        )
        df["pnl"] = df["px side"] * multiplier * abs(df["position"].shift(1))
        df["cum pnl"] = df["pnl"].cumsum()
        self._data = df

    @property
    def dataframe(self) -> DataFrame:
        return self._data
