from decimal import Decimal
from typing import TYPE_CHECKING

from ibapi.contract import Contract

from trade_ibkr.enums import OrderSideConst
from trade_ibkr.utils import make_limit_order

from .interface import Account
from ..action_status import ActionStatus
from ..position import Position, PositionData

if TYPE_CHECKING:
    from trade_ibkr.obj import IBapiBot


class BrokerAccount(Account):
    def __init__(self, /, app: "IBapiBot", position: Position):
        self.app = app
        self.position = position

    def get_current_position_data(self, contract: Contract) -> PositionData | None:
        return self.position.get_position_data(contract)

    def place_order(self, contract: Contract, side: OrderSideConst, quantity: Decimal, px: float):
        order = make_limit_order(side, quantity, px)

        self.app.placeOrder(self.app.next_valid_order_id, contract, order)

    @property
    def action_status(self) -> ActionStatus:
        return self.app.action_status
