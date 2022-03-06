from decimal import Decimal
from typing import TYPE_CHECKING, Union

from ibapi.contract import Contract

from trade_ibkr.enums import OrderSideConst
from trade_ibkr.utils import make_limit_order, make_market_order

from .interface import Account

if TYPE_CHECKING:
    from trade_ibkr.obj import IBapiBase
    from trade_ibkr.model import Position, PositionData


class BrokerAccount(Account):
    def __init__(self, /, app: "IBapiBase", position: "Position"):
        self.app = app
        self.position = position

    def get_current_position_data(self, contract: Contract) -> Union["PositionData", None]:
        return self.position.get_position_data(contract)

    def place_order(self, contract: Contract, side: OrderSideConst, quantity: Decimal, px: float | None):
        if px:
            order = make_limit_order(side, quantity, px)
        else:
            order = make_market_order(side, quantity)

        self.app.placeOrder(self.app.next_valid_order_id, contract, order)
