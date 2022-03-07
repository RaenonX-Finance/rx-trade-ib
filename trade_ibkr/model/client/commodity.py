from dataclasses import dataclass
from decimal import Decimal


@dataclass(kw_only=True)
class Commodity:
    symbol: str
    quantity: Decimal

    def __str__(self):
        return f"{self.symbol} x {self.quantity}"
