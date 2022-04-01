import time
from abc import ABC

from ibapi.contract import ContractDetails
from ibapi.order import Order

from trade_ibkr.enums import reverse_order_side
from trade_ibkr.model import OnOrderFilled, PositionData
from trade_ibkr.utils import get_contract_symbol, make_market_order, print_error, print_log
from .base import IBapiBase


class IBapiOrderBase(IBapiBase, ABC):
    def __init__(self):
        super().__init__()

        self._order_valid_id: int | None = None
        self._order_cache: dict[int, Order] = {}

        self._order_filled_perm_id: int | None = None
        self._order_filled_avg_px: float | None = None
        self._order_on_filled: OnOrderFilled | None = None

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        print_log(f"[API] Fetched next valid order ID {orderId}")
        self._order_valid_id = orderId

    @property
    def next_valid_order_id(self) -> int:
        if not self._order_valid_id:
            print_error("[API] Requested next valid order ID, but it's unavailable - attempt to fetch")
            self.reqIds(-1)

        while not self._order_valid_id:
            print_log("[API] Waiting next valid order ID...")
            time.sleep(0.25)

        ret = self._order_valid_id

        self._order_valid_id += 1

        return ret

    def close_positions_of_contract(self, contract: ContractDetails, position: PositionData):
        print_log(f"Closing positions of [lightblue]{get_contract_symbol(contract)}[/lightblue]")
        order = make_market_order(
            side=reverse_order_side(position.side.order_side),
            quantity=abs(position.position),
        )

        self.placeOrder(self.next_valid_order_id, contract.contract, order)
