import asyncio
import sys
import time
from abc import ABC

from ibapi.commission_report import CommissionReport
from ibapi.contract import Contract
from ibapi.execution import Execution, ExecutionFilter

from trade_ibkr.model import (
    OnExecutionFetched, OnExecutionFetchedEvent, OnExecutionFetchedGetParams, OnExecutionFetchedParams,
    OrderExecution, OrderExecutionCollection,
)
from trade_ibkr.utils import print_error
from .open_order import IBapiOpenOrder
from .position import IBapiPosition


class IBapiExecution(IBapiOpenOrder, IBapiPosition, ABC):
    def __init__(self):
        super().__init__()

        self._execution_cache: dict[str, OrderExecution] = {}
        self._execution_on_fetched: OnExecutionFetched | None = None
        self._execution_on_fetched_params: OnExecutionFetchedGetParams | None = None
        self._execution_on_fetched_params_processed: OnExecutionFetchedParams | None = None

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
            self.request_positions()
            self.request_open_orders()
            self.request_all_executions()
            return

        pnl = commissionReport.realizedPNL
        if pnl == sys.float_info.max:  # Max value PnL means unavailable
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

        self.reqExecutions(self.next_valid_request_id, exec_filter)
