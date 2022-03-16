import asyncio
from abc import ABC
from decimal import Decimal

from ibapi.common import OrderId
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState

from trade_ibkr.const import RISK_MGMT_SL_X, RISK_MGMT_TP_X
from trade_ibkr.enums import OrderSideConst
from trade_ibkr.model import OnOrderFilled, OnOrderFilledEvent
from trade_ibkr.utils import (
    get_contract_identifier, make_limit_order, make_stop_order, make_limit_bracket_order,
    print_error, update_order_price,
)
from .execution import IBapiExecution
from .open_order import IBapiOpenOrder
from .position import IBapiPosition


class IBapiOrderManagement(IBapiExecution, IBapiOpenOrder, IBapiPosition, ABC):
    def _handle_on_order_filled(self, contract: Contract, order: Order):
        if not self._order_on_filled:
            print_error("Order filled handler not set, use `set_on_order_filled()` for setting it.")
            self._order_filled_perm_id = None
            self._order_filled_avg_px = None
            return

        async def execute_after_order_filled():
            await self._order_on_filled(OnOrderFilledEvent(
                identifier=get_contract_identifier(contract),
                symbol=contract.symbol,
                action=order.action,
                quantity=order.filledQuantity,
                fill_px=self._order_filled_avg_px,
            ))

        asyncio.run(execute_after_order_filled())

        self._order_filled_perm_id = None
        self._order_filled_avg_px = None

    def completedOrder(self, contract: Contract, order: Order, orderState: OrderState):
        if order.permId == self._order_filled_perm_id:
            self._handle_on_order_filled(contract, order)

    def orderStatus(
            self, orderId: OrderId, status: str, filled: Decimal,
            remaining: Decimal, avgFillPrice: float, permId: int,
            parentId: int, lastFillPrice: float, clientId: int,
            whyHeld: str, mktCapPrice: float
    ):
        if status in ("Cancelled", "Filled"):
            # Triggered on order cancelled, or filled (along with `openOrder`, on order placed or filled)
            self.request_open_orders()

        if status == "Filled":
            self.request_positions()
            self.request_all_executions()

            if remaining == 0:
                self._order_filled_perm_id = permId
                self._order_filled_avg_px = avgFillPrice
                self.request_completed_orders()

    def _make_new_order(
            self, *,
            side: OrderSideConst, quantity: float, order_px: float | None,
            current_px: float, diff_sma: float, order_id: int, min_tick: float,
            contract_identifier: int,
    ) -> list[Order]:
        quantity = Decimal(quantity)

        # Make order Px = current Px if not specified (intend to order on market Px)
        if not order_px:
            order_px = current_px

        def _make_limit_order_internal() -> list[Order]:
            if (
                    self._has_open_order_of_contract(contract_identifier) or
                    (self._position_data and self._position_data.has_position(contract_identifier))
            ):
                # Has open order / position, make simple LMT order instead
                return [make_limit_order(side, quantity, order_px, order_id)]

            return make_limit_bracket_order(
                side, quantity, order_px, order_id,
                take_profit_px_diff=diff_sma * RISK_MGMT_TP_X,
                stop_loss_px_diff=diff_sma * RISK_MGMT_SL_X,
                min_tick=min_tick
            )

        if not order_px:
            # Market limit
            return _make_limit_order_internal()

        match side:
            case "BUY":
                if order_px < current_px:
                    return _make_limit_order_internal()

                return [make_stop_order(side, quantity, order_px, order_id)]
            case "SELL":
                if order_px > current_px:
                    return _make_limit_order_internal()

                return [make_stop_order(side, quantity, order_px, order_id)]

        raise ValueError(f"Unhandled order side: {side}")

    def _update_order(self, *, existing_order: Order, quantity: float, order_px: float):
        quantity = Decimal(quantity)

        update_order_price(existing_order, order_px)
        existing_order.totalQuantity = quantity

    def place_order(
            self, *,
            contract: Contract, side: OrderSideConst, quantity: float, order_px: float | None,
            current_px: float, diff_sma: float, order_id: int | None, min_tick: float,
    ):
        if order_id:
            # Have order ID means it's order modification
            existing_order = self._order_cache.get(order_id)

            if existing_order:
                self._update_order(existing_order=existing_order, quantity=quantity, order_px=order_px)

                super().placeOrder(order_id, contract, existing_order)
                return

        # Not order modification, create new order
        order_list = self._make_new_order(
            side=side,
            order_px=order_px,
            quantity=quantity,
            current_px=current_px,
            order_id=self.next_valid_order_id,
            diff_sma=diff_sma,
            min_tick=min_tick,
            contract_identifier=get_contract_identifier(contract),
        )

        for order in order_list:
            super().placeOrder(order.orderId, contract, order)

        # Request next valid order ID for future use
        # `-1` as the doc mentioned, the parameter is not being used
        self.reqIds(-1)

    def cancel_order(self, order_id: int):
        self.cancelOrder(order_id)

    def request_completed_orders(self):
        self.reqCompletedOrders(False)

    def set_on_order_filled(self, on_order_filled: OnOrderFilled):
        self._order_on_filled = on_order_filled
