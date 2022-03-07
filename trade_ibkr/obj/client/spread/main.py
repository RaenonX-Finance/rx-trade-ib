import asyncio
import time
from dataclasses import dataclass
from decimal import Decimal

from ibapi.common import OrderId, TickAttrib
from ibapi.contract import Contract
from ibapi.order import Order
from socketio import AsyncClient

from trade_ibkr.enums import SocketEvent
from trade_ibkr.model import (
    BrokerAccount, CommodityPair, GetSpread,
    PxDataPair, UnrealizedPnL,
)
from trade_ibkr.utils import get_order_trigger_price, print_log


@dataclass(kw_only=True)
class PxDataCacheEntry:
    unrlzd_pnl: UnrealizedPnL


@dataclass(kw_only=True)
class PxDataCache:
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


class ClientBotSpread:
    def __init__(self, commodity_pair: CommodityPair, socket_client: AsyncClient):
        super().__init__()

        self._commodity_pair = commodity_pair

        socket_client.on(SocketEvent.PX_UPDATED, self.on_history_px_update)
        socket_client.on(SocketEvent.PX_UPDATED_MARKET, self.on_market_px_update)
        socket_client.on(SocketEvent.POSITION, self.on_position_updated)

    async def on_history_px_update(self):
        pass

    async def on_market_px_update(self):
        pass

    async def on_position_updated(self):
        pass

    def on_px_updated(self):
        pass
        # spread_trading_strategy(SpreadTradeParams(e=e))

    def placeOrder(self, orderId: OrderId, contract: Contract, order: Order):
        self._order_pending = True

        print_log(
            f"[TWS] Place order: "
            f"{order.action} {order.orderType} {contract.localSymbol} x {order.totalQuantity} "
            f"@ {get_order_trigger_price(order)}"
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

    # region Px update

    def _on_px_data_updated(self, start_epoch: float):
        async def execute_on_update():
            await self._on_px_updated(dict(
                account=BrokerAccount(app=self, position=self._position_data),
                commodity_pair=self._commodity_pair,
                px_data_pair=self._px_data_cache.to_px_data_pair(self._commodity_pair.get_spread),
                unrlzd_pnl=self._px_data_cache.to_unrlzd_pnl(),
                has_pending_order=self._order_pending,
                proc_sec=time.time() - start_epoch,
            ))

        asyncio.run(execute_on_update())

    def trigger_market_px_updated(self, contract_id: int, px: float):
        # Tick type of 4 is "LAST"
        # TickAttrib is required to trigger `tickPrice` but doesn't matter here
        market_px_req_id = self._get_market_req_id(contract_id)

        if not market_px_req_id:
            return

        self.tickPrice(market_px_req_id, 4, px, TickAttrib())

    # endregion
