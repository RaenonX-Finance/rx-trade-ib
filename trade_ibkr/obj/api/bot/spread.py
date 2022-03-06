import asyncio
import sys
import time
from dataclasses import dataclass
from decimal import Decimal

from ibapi.common import BarData, OrderId
from ibapi.contract import Contract, ContractDetails
from ibapi.order import Order

from trade_ibkr.model import (
    BrokerAccount, CommodityPair, GetSpread, OnMarketPxUpdatedOfBotSpread, OnMarketPxUpdatedOfBotSpreadEvent,
    PxDataCacheBase, PxDataCacheEntryBase, PxDataPair, UnrealizedPnL,
)
from ..base import IBapiBase, IBapiBasePosition, IBapiBasePx


@dataclass(kw_only=True)
class PxDataCacheEntry(PxDataCacheEntryBase):
    unrlzd_pnl: UnrealizedPnL


@dataclass(kw_only=True)
class PxDataCache(PxDataCacheBase[PxDataCacheEntry]):
    px_req_id_high: int | None = None
    px_req_id_low: int | None = None

    def to_px_data_pair(self, get_spread: GetSpread) -> PxDataPair:
        if not self.px_req_id_high:
            raise ValueError("Px Req ID for buy on high not specified")
        elif not self.px_req_id_low:
            raise ValueError("Px Req ID for buy on low not specified")

        data_on_low = self.data[self.px_req_id_low].data
        data_on_hi = self.data[self.px_req_id_high].data

        return PxDataPair(
            bars_on_low=[data_on_low[key] for key in sorted(data_on_low.keys())],
            bars_on_hi=[data_on_hi[key] for key in sorted(data_on_hi.keys())],
            get_spread=get_spread,
        )

    def to_unrlzd_pnl(self) -> UnrealizedPnL:
        return sum(entry.unrlzd_pnl for entry in self.data.values())


class IBapiBotSpread(IBapiBasePx[PxDataCacheEntry, PxDataCache], IBapiBasePosition, IBapiBase):
    def _init_px_data_cache(self) -> PxDataCache:
        return PxDataCache()

    def _init_px_data_subscription(self, contract: Contract):
        def get_new_cache_entry(period_sec: int):
            return PxDataCacheEntry(
                contract=None,
                contract_og=contract,
                data={},
                period_sec=period_sec,
                unrlzd_pnl=UnrealizedPnL()
            )

        return super()._get_px_data_keep_update(
            contract=contract, duration="86400 S", bar_sizes=["1 min"], period_secs=[60],
            get_new_cache_entry=get_new_cache_entry,
        )

    def __init__(self, commodity_pair: CommodityPair, on_px_updated: OnMarketPxUpdatedOfBotSpread):
        super().__init__()

        self._commodity_pair = commodity_pair
        self._on_px_updated: OnMarketPxUpdatedOfBotSpread = on_px_updated

        self._pnl_req_id_to_contract_req_id: dict[int, int] = {}
        self._order_pending: bool = False

        self._px_data_cache.px_req_id_high = self._init_px_data_subscription(commodity_pair.buy_on_high.contract)
        self._px_data_cache.px_req_id_low = self._init_px_data_subscription(commodity_pair.buy_on_low.contract)

    # region Order

    def placeOrder(self, orderId: OrderId, contract: Contract, order: Order):
        self._order_pending = True

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
        self.reqPnLSingle(req_id_pnl, "all", "", contractDetails.underConId)
        self._pnl_req_id_to_contract_req_id[req_id_pnl] = reqId

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

    def _on_px_data_updated(self, start_epoch: float):
        async def execute_on_update():
            await self._on_px_updated(OnMarketPxUpdatedOfBotSpreadEvent(
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

        self._on_px_data_updated(_time)

    def on_market_px_updated(self, px_req_id: int, px: float):
        self._on_px_data_updated(time.time())

    # endregion
