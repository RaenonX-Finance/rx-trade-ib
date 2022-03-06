import asyncio
import time
from abc import ABC
from dataclasses import dataclass
from typing import TypeVar

from ibapi.common import BarData
from ibapi.contract import Contract

from trade_ibkr.model import (
    OnMarketDataReceived, OnMarketDataReceivedEvent, OnPxDataUpdatedEventNoAccount,
    OnPxDataUpdatedNoAccount, PxData, PxDataCacheBase, PxDataCacheEntryBase,
)
from ..base import IBapiBase, IBapiBasePx


@dataclass(kw_only=True)
class PxDataCacheEntry(PxDataCacheEntryBase, ABC):
    on_update: OnPxDataUpdatedNoAccount

    def to_px_data(self) -> PxData:
        self.last_historical_sent = time.time()

        return PxData(
            contract=self.contract,
            period_sec=self.period_sec,
            bars=[self.data[key] for key in sorted(self.data.keys())]
        )


@dataclass(kw_only=True)
class PxDataCacheEntryOneTime(PxDataCacheEntry):
    pass


@dataclass(kw_only=True)
class PxDataCacheEntryKeepUpdate(PxDataCacheEntry):
    on_update_market: OnMarketDataReceived


E = TypeVar("E", bound=PxDataCacheEntry)


@dataclass(kw_only=True)
class PxDataCache(PxDataCacheBase[E]):
    pass


class IBapiInfoPxData(IBapiBasePx[E, PxDataCache], IBapiBase):
    def _init_px_data_cache(self) -> PxDataCache:
        return PxDataCache()

    # region Historical Data

    @staticmethod
    def _on_px_data_updated(start_epoch: float, px_data_cache_entry: E):
        async def execute_on_update():
            await px_data_cache_entry.on_update(OnPxDataUpdatedEventNoAccount(
                contract=px_data_cache_entry.contract,
                px_data=px_data_cache_entry.to_px_data(),
                proc_sec=time.time() - start_epoch,
            ))

        asyncio.run(execute_on_update())

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        _time = time.time()

        super().historicalDataUpdate(reqId, bar)

        px_data_cache_entry = self._px_data_cache.data[reqId]

        if isinstance(px_data_cache_entry, PxDataCacheEntryKeepUpdate) and px_data_cache_entry.is_send_px_data_ok:
            self._on_px_data_updated(_time, px_data_cache_entry)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        _time = time.time()

        super().historicalDataEnd(reqId, start, end)

        px_data_cache_entry = self._px_data_cache.data[reqId]

        if px_data_cache_entry.is_send_px_data_ok:
            self._on_px_data_updated(_time, px_data_cache_entry)

    # endregion

    # region Market Data

    def on_market_px_updated(self, px_req_id: int, px: float):
        px_data_cache_entry = self._px_data_cache.data[px_req_id]

        if (
                not isinstance(px_data_cache_entry, PxDataCacheEntryKeepUpdate) or
                not px_data_cache_entry.is_send_market_px_data_ok
        ):
            return

        async def execute_on_update():
            await px_data_cache_entry.on_update_market(OnMarketDataReceivedEvent(
                contract=px_data_cache_entry.contract,
                px=px,
            ))

        asyncio.run(execute_on_update())

    # endregion

    def is_all_px_data_ready(self, px_data_req_ids: list[int]) -> bool:
        return self._px_data_cache.is_all_px_data_ready(px_data_req_ids)

    def get_px_data_from_cache(self, req_id: int) -> PxData:
        return self._px_data_cache.data[req_id].to_px_data()

    def get_px_data_keep_update(
            self, *,
            contract: Contract, duration: str, bar_sizes: list[str], period_secs: list[int],
            on_px_data_updated: OnPxDataUpdatedNoAccount,
            on_market_data_received: OnMarketDataReceived,
    ) -> list[int]:
        def get_new_cache_entry(period_sec: int):
            return PxDataCacheEntryKeepUpdate(
                contract=None,
                period_sec=period_sec,
                contract_og=contract,
                data={},
                on_update=on_px_data_updated,
                on_update_market=on_market_data_received,
            )

        return super()._get_px_data_keep_update(
            contract=contract, duration=duration, bar_sizes=bar_sizes, period_secs=period_secs,
            get_new_cache_entry=get_new_cache_entry,
        )
