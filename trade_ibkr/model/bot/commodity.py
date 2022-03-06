from dataclasses import dataclass
from decimal import Decimal

from ibapi.contract import Contract


@dataclass(kw_only=True)
class Commodity:
    contract: Contract
    quantity: Decimal

    def __str__(self):
        return f"{self.contract.localSymbol} x {self.quantity}"
