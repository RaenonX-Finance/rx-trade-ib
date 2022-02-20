import asyncio
import sys
from decimal import Decimal

from ibapi.commission_report import CommissionReport
from ibapi.common import OrderId
from ibapi.contract import Contract
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import Order
from ibapi.order_state import OrderState

from trade_ibkr.enums import OrderSideConst
from trade_ibkr.model import (
    OnExecutionFetchEarliestTime, OnExecutionFetched, OnExecutionFetchedEvent, OnOpenOrderFetched,
    OnOpenOrderFetchedEvent, OnOrderFilled, OnOrderFilledEvent, OnPositionFetched, OnPositionFetchedEvent, OpenOrder,
    OpenOrderBook,
    OrderExecution,
    OrderExecutionCollection, Position, PositionData,
)
from trade_ibkr.utils import (
    get_contract_identifier, get_order_trigger_price, make_limit_order, make_market_order, make_stop_order,
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
        self._execution_fetch_earliest_time: OnExecutionFetchEarliestTime | None = None
        self._execution_group_period_sec: int | None = None
        self._execution_request_ids: set[int] = set()

        self._order_pending_contract: Contract | None = None
        self._order_pending_order: Order | None = None
        self._order_cache: dict[int, Order] = {}

        self._order_filled_perm_id: int | None = None
        self._order_filled_avg_px: float | None = None
        self._order_on_filled: OnOrderFilled | None = None

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
            print(
                "Executions fetched, but no corresponding handler is set. "
                "Use `set_on_executions_fetched()` for setting it.",
                file=sys.stderr,
            )
            return

        if not self._execution_group_period_sec:
            print(
                "Executions fetched, but no corresponding period sec is set. "
                "Use `set_on_executions_fetched()` for setting it.",
                file=sys.stderr,
            )
            return

        async def execute_after_execution_fetched():
            await self._execution_on_fetched(OnExecutionFetchedEvent(
                executions=OrderExecutionCollection(
                    self._execution_cache.values(),
                    self._execution_group_period_sec,
                )
            ))

        asyncio.run(execute_after_execution_fetched())

        self._execution_cache = {}

    def set_on_executions_fetched(
            self,
            on_execution_fetched: OnExecutionFetched,
            on_execution_fetch_earliest_time: OnExecutionFetchEarliestTime,
            period_sec: int
    ):
        self._execution_on_fetched = on_execution_fetched
        self._execution_fetch_earliest_time = on_execution_fetch_earliest_time
        self._execution_group_period_sec = period_sec

    def request_all_executions(self):
        if not self._execution_fetch_earliest_time:
            print("`self._execution_fetch_earliest_time()` must be defined before requesting execution")
            return

        exec_filter = ExecutionFilter()
        exec_filter.time = self._execution_fetch_earliest_time().strftime("%Y%m%d %H:%M:%S")

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
        # Requesting a new order ID should indicate that an order is to be placed
        if not self._order_pending_contract:
            print(
                "Order ID requested, which means there's an order to be placed - but contract is not set",
                file=sys.stderr
            )
            return

        if not self._order_pending_order:
            print(
                "Order ID requested, which means there's an order to be placed - but order is not set",
                file=sys.stderr
            )
            return

        super().placeOrder(orderId, self._order_pending_contract, self._order_pending_order)

    def _make_order(
            self, *,
            side: OrderSideConst, quantity: float, order_px: float | None,
            current_px: float, order_id: int | None
    ) -> Order:
        quantity = Decimal(quantity)

        if not order_px:
            return make_market_order(side, quantity, order_id)

        match side:
            case "BUY":
                if order_px > current_px:
                    return make_stop_order(side, quantity, order_px, order_id)

                return make_limit_order(side, quantity, order_px, order_id)
            case "SELL":
                if order_px > current_px:
                    return make_limit_order(side, quantity, order_px, order_id)

                return make_stop_order(side, quantity, order_px, order_id)

        raise ValueError(f"Unhandled order side: {side}")

    def place_order(
            self, *,
            contract: Contract, side: OrderSideConst, quantity: float, order_px: float | None,
            current_px: float, order_id: int | None,
    ):
        order = self._make_order(
            side=side,
            order_px=order_px,
            quantity=quantity,
            current_px=current_px,
            order_id=order_id,
        )

        if order_id:
            # Have order ID means it's order modification
            existing_order = self._order_cache.get(order_id)
            if existing_order and order.orderType != existing_order.orderType:
                # Order type changed, just fill the order as market
                self.cancel_order(order_id)
                order = self._make_order(
                    side=side,
                    quantity=quantity,
                    current_px=current_px,
                    order_id=None,
                    order_px=None,
                )

            super().placeOrder(order_id, contract, order)
        else:
            # No order ID means it's new order
            self._order_pending_contract = contract
            self._order_pending_order = order

            # Related handling should occur in `nextValidId`
            self.reqIds(-1)

    def cancel_order(self, order_id: int):
        self.cancelOrder(order_id)

    def request_completed_orders(self):
        self.reqCompletedOrders(False)

    # endregion
