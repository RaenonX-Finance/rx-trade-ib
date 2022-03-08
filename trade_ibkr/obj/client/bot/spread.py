import asyncio
import sys
import time
from decimal import Decimal

from ibapi.common import BarData, OrderId, TickAttrib, TickerId
from ibapi.contract import Contract, ContractDetails
from ibapi.order import Order
from ibapi.ticktype import TickType, TickTypeEnum

from trade_ibkr.const import (
    ACCOUNT_NUMBER_ACTUAL, ACCOUNT_NUMBER_DEMO, BOT_POSITION_FETCH_INTERVAL,
    BOT_STRATEGY_CHECK_INTERVAL, IS_DEMO,
)
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

        print_log(f"[BOT - Spread] Subscribe Px update for {contract.localSymbol} ({req_px})")

        return req_px

    def __init__(self, *, commodity_pair: CommodityPair, on_px_updated: OnBotSpreadPxUpdated):
        super().__init__()

        self._commodity_pair = commodity_pair

        self._pnl_req_id_to_contract_req_id: dict[int, int] = {}
        self._order_pending_ids: set[int] = set()
        self._on_px_updated = on_px_updated

        self._last_px_update: float = 0
        self._last_position_fetch: float = 0

        # Don't care on those events
        self.set_on_position_fetched(None)
        self.set_on_open_order_fetched(None)

    def activate(self, port: int, client_id: int):
        super().activate(port, client_id)

        self._px_data_cache.px_req_id_high = (
            self._init_px_data_subscription(self._commodity_pair.buy_on_high.contract)
        )
        self._px_data_cache.px_req_id_low = (
            self._init_px_data_subscription(self._commodity_pair.buy_on_low.contract)
        )
        self.request_positions()

    def _override_commodity_contract(self, contract_req_id: int, contract_details: ContractDetails):
        px_req_id = next(iter(self._contract_req_id_to_px_req_id[contract_req_id]))
        if px_req_id == self._px_data_cache.px_req_id_high:
            self._commodity_pair.buy_on_high.contract = contract_details.contract
        elif px_req_id == self._px_data_cache.px_req_id_low:
            self._commodity_pair.buy_on_low.contract = contract_details.contract

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)

        self._request_pnl_single(reqId, contractDetails)
        self._override_commodity_contract(reqId, contractDetails)

    # region Order

    def placeOrder(self, orderId: OrderId, contract: Contract, order: Order):
        self._order_pending_ids.add(orderId)

        px = get_order_trigger_price(order)

        print_log(
            f"[TWS] Place order #{orderId}: "
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
        if status == "Filled":
            print_log(f"[TWS] Order #{orderId} filled")

            if orderId in self._order_pending_ids:
                # `orderStatus` is somehow triggered twice on fill
                self._order_pending_ids.remove(orderId)

            self.request_positions()

    # endregion

    # region Position tracking

    def positionEnd(self):
        super().positionEnd()

        self._last_position_fetch = time.time()

    # endregion

    # region PnL tracking

    def _request_pnl_single(self, contract_req_id: int, contract_details: ContractDetails):
        req_id_pnl = self.next_valid_request_id
        self.reqPnLSingle(
            req_id_pnl,
            ACCOUNT_NUMBER_DEMO if IS_DEMO else ACCOUNT_NUMBER_ACTUAL,
            "",
            contract_details.underConId
        )
        self._pnl_req_id_to_contract_req_id[req_id_pnl] = contract_req_id

        print_log(f"[TWS] Subscribe PnL of {contract_details.underSymbol}")

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
        now = time.time()

        if now - self._last_px_update < BOT_STRATEGY_CHECK_INTERVAL or self._position_fetching:
            return

        self._last_px_update = now

        if not self._position_data or now - self._last_position_fetch > BOT_POSITION_FETCH_INTERVAL:
            self.request_positions()

            if not self._position_data:
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
                has_pending_order=bool(self._order_pending_ids),
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
