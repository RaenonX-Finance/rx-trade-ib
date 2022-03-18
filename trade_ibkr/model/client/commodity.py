from dataclasses import dataclass
from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.utils import get_basic_contract_symbol


@dataclass(kw_only=True)
class Commodity:
    contract: Contract
    quantity: Decimal

    def __str__(self):
        return f"{get_basic_contract_symbol(self.contract)} x {self.quantity}"
