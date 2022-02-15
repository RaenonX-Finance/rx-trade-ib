import asyncio
import sys
from datetime import datetime
from decimal import Decimal

from ibapi.commission_report import CommissionReport
from ibapi.common import OrderId
from ibapi.contract import Contract
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import Order
from ibapi.order_state import OrderState

from trade_ibkr.model import (
    OnExecutionFetched, OnExecutionFetchedEvent, OnOpenOrderFetched, OnOpenOrderFetchedEvent, OnPositionFetched,
    OnPositionFetchedEvent,
    OpenOrder, OpenOrderBook, OrderExecution, OrderExecutionCollection, Position, PositionData,
)
from .base import IBapiInfoBase


class IBapiInfoPortfolio(IBapiInfoBase):
    def __init__(self):
        super().__init__()

        self._position_data_list: list[PositionData] = []
        self._position_on_fetched: OnPositionFetched | None = None

        self._open_order_list: list[OpenOrder] = []
        self._open_order_on_fetched: OnOpenOrderFetched | None = None
        self._open_order_processing: bool = False

        self._execution_cache: dict[str, OrderExecution] = {}
        self._execution_on_fetched: OnExecutionFetched | None = None
        self._execution_group_period_sec: int | None = None
        self._execution_earliest_time: datetime | None = None
        self._execution_request_ids: set[int] = set()

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
                "Use `set_on_position_fetched()` for setting the handler.",
                file=sys.stderr,
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
            price=order.lmtPrice or order.auxPrice,
            quantity=order.totalQuantity,
            side=order.action,
        ))

    def openOrderEnd(self):
        self._open_order_processing = False

        if not self._open_order_on_fetched:
            print(
                "Open order fetched, but no corresponding handler is set. "
                "Use `set_on_open_order_fetched()` for setting the handler.",
                file=sys.stderr,
            )
            return

        async def execute_after_open_order_fetched():
            await self._open_order_on_fetched(OnOpenOrderFetchedEvent(
                open_order=OpenOrderBook(self._open_order_list)
            ))

        asyncio.run(execute_after_open_order_fetched())

        self._open_order_list = []

    def set_on_open_order_fetched(self, on_open_order_fetched: OnOpenOrderFetched):
        self._open_order_on_fetched = on_open_order_fetched

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
                "Use `set_on_executions_fetched()` for setting the handler.",
                file=sys.stderr,
            )
            return

        if not self._execution_group_period_sec:
            print(
                "Executions fetched, but no corresponding period sec is set. "
                "Use `set_on_executions_fetched()` for setting the handler.",
                file=sys.stderr,
            )
            return

        async def execute_after_exection_fetched():
            await self._execution_on_fetched(OnExecutionFetchedEvent(
                executions=OrderExecutionCollection(self._execution_cache.values(), self._execution_group_period_sec)
            ))

        asyncio.run(execute_after_exection_fetched())

        self._execution_cache = {}

    def set_on_executions_fetched(self, on_executions_fetched: OnExecutionFetched, period_sec: int):
        self._execution_on_fetched = on_executions_fetched
        self._execution_group_period_sec = period_sec

    # endregion

    # region Order

    def placeOrder(self, orderId: OrderId, contract: Contract, order: Order):
        super().placeOrder(orderId, contract, order)

        self.action_status.order_pending = True

    def orderStatus(
            self, orderId: OrderId, status: str, filled: Decimal,
            remaining: Decimal, avgFillPrice: float, permId: int,
            parentId: int, lastFillPrice: float, clientId: int,
            whyHeld: str, mktCapPrice: float
    ):
        if status in ("Submitted", "Cancelled") and not self._open_order_processing:
            # `self._open_order_processing` to avoid re-triggering this method, causing pace violation
            self._on_order_updated()

    def _on_order_completed(self):
        self.request_positions()
        self.request_open_orders()
        if self._execution_earliest_time:
            self.request_all_executions(self._execution_earliest_time)

    def _on_order_updated(self):
        self.request_open_orders()

    # endregion

    def request_positions(self):
        self.reqPositions()

    def request_open_orders(self):
        self._open_order_processing = True
        self.reqAllOpenOrders()

    def request_all_executions(self, earliest_time: datetime):
        self._execution_earliest_time = earliest_time

        exec_filter = ExecutionFilter()
        exec_filter.time = earliest_time.strftime("%Y%m%d %H:%M:%S")

        request_id = self.next_valid_request_id
        self._execution_request_ids.add(request_id)
        self.reqExecutions(request_id, exec_filter)
