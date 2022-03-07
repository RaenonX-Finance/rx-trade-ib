from dataclasses import dataclass
from typing import Callable, TypeAlias

from pandas import Series

from .commodity import Commodity


GetSpread: TypeAlias = Callable[[Series, Series], Series]


@dataclass(kw_only=True)
class CommodityPair:
    buy_on_high: Commodity
    buy_on_low: Commodity

    get_spread: GetSpread

    @property
    def commodities(self) -> [Commodity, Commodity]:
        return [self.buy_on_high, self.buy_on_low]

    def __str__(self):
        return f"{self.buy_on_high} on H / {self.buy_on_low} on L"
