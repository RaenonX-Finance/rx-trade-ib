from dataclasses import dataclass
from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.enums import OrderSideConst
from trade_ibkr.utils import get_contract_identifier


@dataclass(kw_only=True)
class OpenOrder:
    order_id: int
    contract: Contract
    price: float
    quantity: Decimal
    side: OrderSideConst


class OpenOrderBook:
    def __init__(self, open_order: list[OpenOrder]):
        self._orders = {}
        for order in open_order:
            identifier = get_contract_identifier(order.contract)
            if identifier not in self._orders:
                self._orders[identifier] = []

            self._orders[identifier].append(order)

    @property
    def orders(self) -> dict[int, list[OpenOrder]]:
        return self._orders
