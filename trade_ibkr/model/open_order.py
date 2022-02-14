from dataclasses import dataclass
from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.enums import OrderSide, OrderType
from trade_ibkr.utils import get_contract_identifier


@dataclass(kw_only=True)
class OpenOrder:
    contract: Contract
    type_: OrderType
    price: float
    quantity: Decimal
    side: OrderSide


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
