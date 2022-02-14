import asyncio
import time
from decimal import Decimal

from ibapi.common import OrderId
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState

from trade_ibkr.model import (
    OnOpenOrderFetched, OnOpenOrderFetchedEvent, OnPositionFetched, OnPositionFetchedEvent,
    OpenOrder, OpenOrderBook, Position, PositionData,
)
from .base import IBapiInfoBase


class IBapiInfoPortfolio(IBapiInfoBase):
    def __init__(self):
        super().__init__()

        self._position_data_list: list[PositionData] = []
        self._position_on_fetched: OnPositionFetched | None = None

        self._open_order_list: list[OpenOrder] = []
        self._open_order_on_fetched: OnOpenOrderFetched | None = None

    # region Position

    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        self._position_data_list.append(PositionData(
            contract=contract,
            position=position,
            avg_cost=avgCost,
        ))

    def positionEnd(self):
        if not self._position_on_fetched:
            print(
                "Position fetched, but no correspoding handler is set. "
                "Use `set_on_position_fetched()` for setting the handler."
            )
            return

        async def execute_after_position_end():
            await self._position_on_fetched(OnPositionFetchedEvent(position=Position(self._position_data_list)))

        asyncio.run(execute_after_position_end())

        self._position_data_list = []

    def set_on_position_fetched(self, on_position_fetched: OnPositionFetched):
        self._position_on_fetched = on_position_fetched

    # endregion

    # region Open Order

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        self._open_order_list.append(OpenOrder(
            contract=contract,
            type_=order.orderType,
            price=order.lmtPrice,
            quantity=order.totalQuantity,
            side=order.action,
        ))

    def openOrderEnd(self):
        if not self._open_order_on_fetched:
            print(
                "Open order fetched, but no correspoding handler is set. "
                "Use `set_on_open_order_fetched()` for setting the handler."
            )
            return

        async def execute_after_open_order_fetched():
            await self._open_order_on_fetched(OnOpenOrderFetchedEvent(open_order=OpenOrderBook(self._open_order_list)))

        asyncio.run(execute_after_open_order_fetched())

        self._open_order_list = []

    def set_on_open_order_fetched(self, on_open_order_fetched: OnOpenOrderFetched):
        self._open_order_on_fetched = on_open_order_fetched

    # endregion

    # region Order

    @property
    def next_valid_order_id(self) -> int:
        return int(time.time())

    def placeOrder(self, orderId: OrderId, contract: Contract, order: Order):
        super().placeOrder(orderId, contract, order)

        self.action_status.order_pending = True

    def orderStatus(
            self, orderId: OrderId, status: str, filled: Decimal,
            remaining: Decimal, avgFillPrice: float, permId: int,
            parentId: int, lastFillPrice: float, clientId: int,
            whyHeld: str, mktCapPrice: float
    ):
        if status == "Filled":
            self.action_status.order_pending = False
            self.action_status.order_executed_on_current_k = True
            self.refresh_positions()

    # endregion

    def refresh_positions(self):
        self.reqPositions()

    def refresh_open_orders(self):
        self.reqAllOpenOrders()
