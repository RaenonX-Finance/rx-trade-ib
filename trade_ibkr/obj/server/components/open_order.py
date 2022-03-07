import asyncio
from abc import ABC

from ibapi.common import OrderId
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState

from trade_ibkr.model import OnOpenOrderFetched, OnOpenOrderFetchedEvent, OpenOrder, OpenOrderBook
from trade_ibkr.utils import get_order_trigger_price, print_error
from .order_base import IBapiOrderBase


class IBapiOpenOrder(IBapiOrderBase, ABC):
    def __init__(self):
        super().__init__()

        self._open_order_list: list[OpenOrder] | None = None
        self._open_order_on_fetched: OnOpenOrderFetched | None = None

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        if self._open_order_list is None:
            # Manually dispatch a request event because it's not triggered on-demand
            # > `_open_order_list` is `None` means it's not manually requested
            self.request_open_orders()
            return

        self._order_cache[orderId] = order
        self._open_order_list.append(OpenOrder(
            order_id=orderId,
            contract=contract,
            price=get_order_trigger_price(order),
            quantity=order.totalQuantity,
            side=order.action,
            parent_id=order.parentId,
        ))

    def openOrderEnd(self):
        if not self._open_order_on_fetched:
            print_error(
                "Open order fetched, but no corresponding handler is set. "
                "Use `set_on_open_order_fetched()` for setting it.",
            )
            return

        async def execute_after_open_order_fetched():
            await self._open_order_on_fetched(OnOpenOrderFetchedEvent(
                open_order=OpenOrderBook(self._open_order_list or [])
            ))

        asyncio.run(execute_after_open_order_fetched())

        self._open_order_list = None

    def set_on_open_order_fetched(self, on_open_order_fetched: OnOpenOrderFetched):
        self._open_order_on_fetched = on_open_order_fetched

    def request_open_orders(self):
        if self._open_order_list is not None:
            # Another request is processing, ignore the current one
            return

        self._open_order_list = []
        self.reqOpenOrders()
