import asyncio
from abc import ABC
from typing import Literal

from ibapi.common import OrderId
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState

from trade_ibkr.model import OnOpenOrderFetched, OnOpenOrderFetchedEvent, OpenOrder, OpenOrderBook
from trade_ibkr.utils import get_contract_identifier, get_order_trigger_price, print_error
from .order_base import IBapiOrderBase


class IBapiOpenOrder(IBapiOrderBase, ABC):
    def __init__(self):
        super().__init__()

        self._open_order_list: list[OpenOrder] = []
        self._open_order_fetching: bool = False
        self._open_order_on_fetched: OnOpenOrderFetched | None | Literal["UNDEFINED"] = "UNDEFINED"

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        if not self._open_order_fetching:
            # Manually dispatch a request event because it's not triggered on-demand
            self.request_open_orders()
            return

        self._order_cache[orderId] = order
        self._open_order_list.append(OpenOrder(
            order_id=orderId,
            contract=contract,
            price=get_order_trigger_price(order),
            quantity=order.totalQuantity,
            side=order.action,
            type_=order.orderType,
            parent_id=order.parentId,
        ))

    def openOrderEnd(self):
        self._open_order_fetching = False

        if self._open_order_on_fetched == "UNDEFINED":
            print_error(
                "[TWS] Open order fetched, but no corresponding handler is set. "
                "Use `set_on_open_order_fetched()` for setting it.\n"
                "If this is intended, call `set_on_open_order_fetched(None)`",
            )
            self._open_order_list = []
            return
        elif not self._open_order_on_fetched:
            self._open_order_list = []
            return

        async def execute_after_open_order_fetched():
            # noinspection PyCallingNonCallable
            await self._open_order_on_fetched(OnOpenOrderFetchedEvent(
                open_order=OpenOrderBook(self._open_order_list)
            ))

        asyncio.run(execute_after_open_order_fetched())

    def set_on_open_order_fetched(self, on_open_order_fetched: OnOpenOrderFetched | None):
        self._open_order_on_fetched = on_open_order_fetched

    def request_open_orders(self):
        if self._open_order_fetching:
            # Another request is processing, ignore the current one
            return

        self._open_order_list = []
        self._open_order_fetching = True
        self.reqOpenOrders()

    def _has_open_order_of_contract(self, contract_identifier: int) -> bool:
        return any(
            get_contract_identifier(open_order.contract) == contract_identifier
            for open_order in self._open_order_list
        )
