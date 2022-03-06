import asyncio
import sys
import time
from decimal import Decimal

from ibapi.commission_report import CommissionReport
from ibapi.common import OrderId
from ibapi.contract import Contract
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import Order
from ibapi.order_state import OrderState

from trade_ibkr.const import AMPL_COEFF_SL, AMPL_COEFF_TP
from trade_ibkr.enums import OrderSideConst
from trade_ibkr.model import (
    OnExecutionFetched, OnExecutionFetchedEvent,
    OnExecutionFetchedGetParams, OnExecutionFetchedParams,
    OnOpenOrderFetched, OnOpenOrderFetchedEvent,
    OnOrderFilled, OnOrderFilledEvent,
    OnPositionFetched, OnPositionFetchedEvent,
    OpenOrder, OpenOrderBook,
    OrderExecution, OrderExecutionCollection,
    Position, PositionData,
)
from trade_ibkr.utils import (
    get_contract_identifier, get_order_trigger_price,
    make_limit_bracket_order, make_market_order, make_stop_order,
    print_error, print_log, update_order_price,
)
from .base import IBapiInfoBase


class IBapiInfoPortfolio(IBapiInfoBase):
    def __init__(self):
        super().__init__()

        self._position_data_list: list[PositionData] = []
        self._position_on_fetched: OnPositionFetched | None = None

        self._open_order_list: list[OpenOrder] | None = None
        self._open_order_on_fetched: OnOpenOrderFetched | None = None
        self._open_order_fetching: bool = False

        self._execution_cache: dict[str, OrderExecution] = {}
        self._execution_on_fetched: OnExecutionFetched | None = None
        self._execution_on_fetched_params: OnExecutionFetchedGetParams | None = None
        self._execution_on_fetched_params_processed: OnExecutionFetchedParams | None = None
        self._execution_request_ids: set[int] = set()

        self._order_cache: dict[int, Order] = {}

        self._order_filled_perm_id: int | None = None
        self._order_filled_avg_px: float | None = None
        self._order_on_filled: OnOrderFilled | None = None
        self._order_valid_id: int | None = None

    # region Action on Order Updated

    def _on_order_completed(self):
        self.request_positions()
        self.request_open_orders()
        self.request_all_executions()

    # endregion

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
                "Position fetched, but no corresponding handler is set. "
                "Use `set_on_position_fetched()` for setting it.",
                file=sys.stderr,
            )
            return

        async def execute_after_position_end():
            await self._position_on_fetched(OnPositionFetchedEvent(position=Position(self._position_data_list)))

        asyncio.run(execute_after_position_end())

        self._position_data_list = []

    def set_on_position_fetched(self, on_position_fetched: OnPositionFetched):
        self._position_on_fetched = on_position_fetched

    def request_positions(self):
        self.reqPositions()

    # endregion

    # region Open Order

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
            print(
                "Open order fetched, but no corresponding handler is set. "
                "Use `set_on_open_order_fetched()` for setting it.",
                file=sys.stderr,
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

    # endregion

    # region Order Executions

    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        self._execution_cache[execution.execId] = OrderExecution(
            exec_id=execution.execId,
            order_id=execution.permId,
            contract=contract,
            local_time_original=execution.time,
            side=execution.side,
            cumulative_quantity=execution.cumQty,
            avg_price=execution.avgPrice,
        )

    def commissionReport(self, commissionReport: CommissionReport):
        if commissionReport.execId not in self._execution_cache:
            # This method is triggered when an order is filled
            # If `execId` is not in the execution cache, it should be a signal of "order filled"
            self._on_order_completed()
            return

        pnl = commissionReport.realizedPNL
        if pnl == sys.float_info.max:  # Max value PNL means unavailable
            return

        self._execution_cache[commissionReport.execId].realized_pnl = commissionReport.realizedPNL

    def execDetailsEnd(self, reqId: int):
        if not self._execution_on_fetched:
            print_error(
                "Executions fetched, but no corresponding handler is set. "
                "Use `set_on_executions_fetched()` for setting it.",
            )
            return

        if not self._execution_on_fetched_params_processed:
            self._execution_on_fetched_params_processed = self._execution_on_fetched_params()

        _time = time.time()

        async def execute_after_execution_fetched():
            await self._execution_on_fetched(OnExecutionFetchedEvent(
                executions=OrderExecutionCollection(
                    self._execution_cache.values(),
                    self._execution_on_fetched_params_processed,
                ),
                proc_sec=time.time() - _time
            ))

        asyncio.run(execute_after_execution_fetched())

        self._execution_cache = {}

    def set_on_executions_fetched(
            self,
            on_execution_fetched: OnExecutionFetched,
            on_execution_fetched_params: OnExecutionFetchedGetParams,
    ):
        self._execution_on_fetched = on_execution_fetched
        self._execution_on_fetched_params = on_execution_fetched_params

    def request_all_executions(self):
        if not self._execution_on_fetched_params:
            print_error("`self._execution_fetch_earliest_time()` must be defined before requesting execution")
            return

        self._execution_on_fetched_params_processed = self._execution_on_fetched_params()

        exec_filter = ExecutionFilter()
        exec_filter.time = self._execution_on_fetched_params_processed.earliest_time.strftime("%Y%m%d %H:%M:%S")

        request_id = self.next_valid_request_id
        self._execution_request_ids.add(request_id)
        self.reqExecutions(request_id, exec_filter)

    # endregion

    # region Order Management

    def _handle_on_order_filled(self, contract: Contract, order: Order):
        if order.permId != self._order_filled_perm_id:
            return

        if not self._order_on_filled:
            print(
                "Order filled handler not set, use `set_on_order_filled()` for setting it",
                file=sys.stderr
            )

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
        self._handle_on_order_filled(contract, order)

    def set_on_order_filled(self, on_order_filled: OnOrderFilled):
        self._order_on_filled = on_order_filled

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

    def nextValidId(self, orderId: int):
        print_log(f"[API] Fetched next valid order ID {orderId}")
        self._order_valid_id = orderId

    def _make_new_order(
            self, *,
            side: OrderSideConst, quantity: float, order_px: float | None,
            current_px: float, amplitude_hc: float, order_id: int, min_tick: float,
    ) -> list[Order]:
        quantity = Decimal(quantity)

        if not order_px:
            return [make_market_order(side, quantity, order_id)]

        match side:
            case "BUY":
                if order_px < current_px:
                    return make_limit_bracket_order(
                        side, quantity, order_px, order_id,
                        take_profit_px_diff=amplitude_hc * AMPL_COEFF_TP,
                        stop_loss_px_diff=amplitude_hc * AMPL_COEFF_SL,
                        min_tick=min_tick,
                    )

                return [make_stop_order(side, quantity, order_px, order_id)]
            case "SELL":
                if order_px > current_px:
                    return make_limit_bracket_order(
                        side, quantity, order_px, order_id,
                        take_profit_px_diff=amplitude_hc * AMPL_COEFF_TP,
                        stop_loss_px_diff=amplitude_hc * AMPL_COEFF_SL,
                        min_tick=min_tick,
                    )

                return [make_stop_order(side, quantity, order_px, order_id)]

        raise ValueError(f"Unhandled order side: {side}")

    def _update_order(self, *, existing_order: Order, quantity: float, order_px: float):
        quantity = Decimal(quantity)

        update_order_price(existing_order, order_px)
        existing_order.totalQuantity = quantity

    def place_order(
            self, *,
            contract: Contract, side: OrderSideConst, quantity: float, order_px: float | None,
            current_px: float, amplitude_hc: float, order_id: int | None, min_tick: float,
    ):
        if order_id:
            # Have order ID means it's order modification
            existing_order = self._order_cache.get(order_id)

            if existing_order:
                self._update_order(existing_order=existing_order, quantity=quantity, order_px=order_px)

                super().placeOrder(order_id, contract, existing_order)
                return

        if not self._order_valid_id:
            print_error("Valid order ID unavailable, request order ID first")
            return

        # Not order modification, create new order
        order_list = self._make_new_order(
            side=side,
            order_px=order_px,
            quantity=quantity,
            current_px=current_px,
            order_id=self._order_valid_id,
            amplitude_hc=amplitude_hc,
            min_tick=min_tick,
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

    # endregion
