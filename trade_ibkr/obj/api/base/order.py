import time
from abc import ABC

from trade_ibkr.utils import print_error, print_log
from .common import IBapiBaseCommon


class IBapiBaseOrder(IBapiBaseCommon, ABC):
    def __init__(self):
        super().__init__()

        self._order_valid_id: int | None = None

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

        return self._order_valid_id
