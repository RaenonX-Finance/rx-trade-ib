import asyncio
import sys
import time
from decimal import Decimal

from ibapi.common import BarData, OrderId, TickAttrib, TickerId
from ibapi.contract import Contract, ContractDetails
from ibapi.order import Order
from ibapi.ticktype import TickType, TickTypeEnum

from trade_ibkr.const import ACCOUNT_NUMBER_ACTUAL, ACCOUNT_NUMBER_DEMO, IS_DEMO
from trade_ibkr.model import (
    BrokerAccount, CommodityPair, OnBotSpreadPxUpdated, OnBotSpreadPxUpdatedEvent, PxDataPairCache,
    PxDataPairCacheEntry, UnrealizedPnL,
)
from trade_ibkr.utils import get_order_trigger_price, print_error, print_log
from ...server import IBapiServer


class IBautoBotSpread(IBapiServer):
    def _init_get_px_data_cache(self) -> PxDataPairCache:
        return PxDataPairCache()

    def _init_px_data_subscription(self, contract: Contract) -> int:
        req_contract = self.request_contract_data(contract)
        req_market = self._request_px_data_market(contract)
        req_px = self._request_px_data(contract=contract, duration="86400 S", bar_size="1 min", keep_update=True)

        self._px_req_id_to_contract_req_id[req_px] = req_contract
        self._contract_req_id_to_px_req_id[req_contract].add(req_px)
        self._px_market_to_px_data[req_market].add(req_px)

        self._px_data_cache.data[req_px] = PxDataPairCacheEntry(
            contract=None,
            contract_og=contract,
            data={},
            period_sec=60,
            on_update=None,
            unrlzd_pnl=UnrealizedPnL()
        )

        return req_px

    def __init__(self, *, commodity_pair: CommodityPair, on_px_updated: OnBotSpreadPxUpdated):
        super().__init__()

        self._commodity_pair = commodity_pair

        self._pnl_req_id_to_contract_req_id: dict[int, int] = {}
        self._order_pending: bool = False
        self._on_px_updated = on_px_updated

        # Bot doesn't care after the position is fetched
        self.set_on_position_fetched(None)

    def activate(self, port: int, client_id: int):
        super().activate(port, client_id)

        self._px_data_cache.px_req_id_high = (
            self._init_px_data_subscription(self._commodity_pair.buy_on_high.contract)
        )
        self._px_data_cache.px_req_id_low = (
            self._init_px_data_subscription(self._commodity_pair.buy_on_low.contract)
        )

    # region Order

    def placeOrder(self, orderId: OrderId, contract: Contract, order: Order):
        self._order_pending = True

        px = get_order_trigger_price(order)

        print_log(
            f"[TWS] Place order: "
            f"{order.action} {order.orderType} {contract.localSymbol} x {order.totalQuantity} "
            f"@ {'MKT' if px == sys.float_info.max else px}"
        )
        super().placeOrder(orderId, contract, order)

    def orderStatus(
            self, orderId: OrderId, status: str, filled: Decimal,
            remaining: Decimal, avgFillPrice: float, permId: int,
            parentId: int, lastFillPrice: float, clientId: int,
            whyHeld: str, mktCapPrice: float
    ):
        super().orderStatus(
            orderId, status, filled, remaining, avgFillPrice, permId,
            parentId, lastFillPrice, clientId, whyHeld, mktCapPrice
        )

        if status == "Filled":
            self._order_pending = False
            self.request_positions()

    # endregion

    # region PnL tracking

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)

        req_id_pnl = self.next_valid_request_id
        self.reqPnLSingle(
            req_id_pnl,
            ACCOUNT_NUMBER_DEMO if IS_DEMO else ACCOUNT_NUMBER_ACTUAL,
            "",
            contractDetails.underConId
        )
        self._pnl_req_id_to_contract_req_id[req_id_pnl] = reqId

        print_log(f"[TWS] Subscribe PnL of {contractDetails.underSymbol}")

    def pnlSingle(
            self, reqId: int, pos: Decimal, dailyPnL: float, unrealizedPnL: float, realizedPnL: float, value: float
    ):
        super().pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)

        if unrealizedPnL == sys.float_info.max:  # Max value PnL means unavailable
            return

        contract_req_id = self._pnl_req_id_to_contract_req_id[reqId]
        for px_req_id in self._contract_req_id_to_px_req_id[contract_req_id]:
            self._px_data_cache.data[px_req_id].unrlzd_pnl.update(unrealizedPnL)

    # endregion

    # region Px update

    def _px_data_updated(self, start_epoch: float):
        if not self._position_data:
            self.request_positions()
            return

        if not self._px_data_cache.is_data_ready():
            print_error("[yellow][TWS] Px data not ready - spread px updated event not triggered[/yellow]")
            return

        async def execute_on_update():
            await self._on_px_updated(OnBotSpreadPxUpdatedEvent(
                account=BrokerAccount(app=self, position=self._position_data),
                commodity_pair=self._commodity_pair,
                px_data_pair=self._px_data_cache.to_px_data_pair(self._commodity_pair.get_spread),
                unrlzd_pnl=self._px_data_cache.to_unrlzd_pnl(),
                has_pending_order=self._order_pending,
                proc_sec=time.time() - start_epoch,
            ))

        asyncio.run(execute_on_update())

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        _time = time.time()

        super().historicalDataUpdate(reqId, bar)
        self._px_data_updated(_time)

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        super().tickPrice(reqId, tickType, price, attrib)

        name = TickTypeEnum.idx2name[tickType]

        if name != "LAST":
            return

        self._px_data_updated(time.time())

    # endregion
