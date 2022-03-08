import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, TypeVar

from ibapi.common import BarData, TickAttrib, TickerId
from ibapi.contract import Contract
from ibapi.ticktype import TickType, TickTypeEnum

from trade_ibkr.model import (
    OnMarketDataReceived, OnMarketDataReceivedEvent, OnPxDataUpdatedEventNoAccount, OnPxDataUpdatedNoAccount,
    PxData, PxDataCache, PxDataCacheEntry,
)
from .contract import IBapiContract


@dataclass(kw_only=True)
class PxDataCacheEntryOneTime(PxDataCacheEntry):
    pass


@dataclass(kw_only=True)
class PxDataCacheEntryKeepUpdate(PxDataCacheEntry):
    on_update_market: OnMarketDataReceived


T = TypeVar("T", bound=PxDataCache)


class IBapiPx(IBapiContract, ABC):
    @abstractmethod
    def _init_get_px_data_cache(self) -> T:
        raise NotImplementedError()

    def __init__(self):
        super().__init__()

        self._px_data_cache: T = self._init_get_px_data_cache()
        self._px_req_id_to_contract_req_id: dict[int, int] = {}
        self._px_market_to_px_data: DefaultDict[int, set[int]] = defaultdict(set)
        self._contract_req_id_to_px_req_id: DefaultDict[int, set[int]] = defaultdict(set)

    # region Historical

    def _on_historical_data_return(self, req_id_px: int, bar: BarData, /, is_realtime_update: bool):
        cache_entry = self._px_data_cache.data[req_id_px]

        if contract_req_id := self._px_req_id_to_contract_req_id.get(req_id_px):
            # Add contract detail to PxData object
            cache_entry.contract = self._contract_data[contract_req_id]

        cache_entry.update_latest_history(bar, is_realtime_update=is_realtime_update)

    def _on_px_data_updated(self, start_epoch: float, px_data_cache_entry: PxDataCacheEntry):
        if not px_data_cache_entry.on_update:
            return

        async def execute_on_update():
            await px_data_cache_entry.on_update(OnPxDataUpdatedEventNoAccount(
                contract=px_data_cache_entry.contract,
                px_data=px_data_cache_entry.to_px_data(),
                proc_sec=time.time() - start_epoch,
            ))

        asyncio.run(execute_on_update())

    def _request_px_data(self, *, contract: Contract, duration: str, bar_size: str, keep_update: bool) -> int:
        request_id = self.next_valid_request_id

        self.reqHistoricalData(request_id, contract, "", duration, bar_size, "TRADES", 0, 2, keep_update, [])

        return request_id

    def historicalData(self, reqId: int, bar: BarData):
        super().historicalData(reqId, bar)

        self._on_historical_data_return(reqId, bar, is_realtime_update=False)

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        _time = time.time()
        super().historicalDataUpdate(reqId, bar)

        self._on_historical_data_return(reqId, bar, is_realtime_update=True)

        px_data_cache_entry = self._px_data_cache.data[reqId]

        if isinstance(px_data_cache_entry, PxDataCacheEntryKeepUpdate) and px_data_cache_entry.is_send_px_data_ok:
            # Update Px data if it should keep updated
            self._on_px_data_updated(_time, px_data_cache_entry)

        if px_data_cache_entry.no_market_data_update:
            # Re-trigger market data feed if stopped
            req_market = self._request_px_data_market(px_data_cache_entry.contract_og)
            self._px_market_to_px_data[req_market].add(reqId)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        _time = time.time()

        super().historicalDataEnd(reqId, start, end)

        px_data_cache_entry = self._px_data_cache.data[reqId]

        if px_data_cache_entry.is_send_px_data_ok:
            self._on_px_data_updated(_time, px_data_cache_entry)

    # endregion

    # region Market

    def _request_px_data_market(self, contract: Contract) -> int:
        request_id = self.next_valid_request_id

        self.reqMktData(request_id, contract, "", False, False, [])

        return request_id

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        name = TickTypeEnum.idx2name[tickType]

        if name != "LAST":
            return

        px_req_id = next(px_req_id for px_req_id in self._px_market_to_px_data[reqId])

        px_data_cache_entry = self._px_data_cache.data[px_req_id]

        if (
                not isinstance(px_data_cache_entry, PxDataCacheEntryKeepUpdate) or
                not px_data_cache_entry.is_send_market_px_data_ok
        ):
            return

        async def execute_on_update():
            await px_data_cache_entry.on_update_market(OnMarketDataReceivedEvent(
                contract=px_data_cache_entry.contract,
                px=price,
            ))

        asyncio.run(execute_on_update())

        # Must be placed after `is_send_market_px_data_ok`
        self._px_data_cache.data[px_req_id].update_latest_market(price)

    # endregion

    def get_px_data_from_cache(self, req_id: int) -> PxData:
        return self._px_data_cache.data[req_id].to_px_data()

    def get_px_data_keep_update(
            self, *,
            contract: Contract, duration: str, bar_sizes: list[str], period_secs: list[int],
            on_px_data_updated: OnPxDataUpdatedNoAccount,
            on_market_data_received: OnMarketDataReceived,
    ) -> list[int]:
        if len(period_secs) != len(bar_sizes):
            raise ValueError(
                f"`period_secs` ({len(period_secs)}) should have the same length of `bar_sizes` ({len(bar_sizes)})"
            )

        req_px_ids: list[int] = []

        req_contract = self.request_contract_data(contract)
        req_market = self._request_px_data_market(contract)

        for bar_size, period_sec in zip(bar_sizes, period_secs):
            req_px = self._request_px_data(contract=contract, duration=duration, bar_size=bar_size, keep_update=True)
            self._px_req_id_to_contract_req_id[req_px] = req_contract
            self._contract_req_id_to_px_req_id[req_contract].add(req_px)
            self._px_market_to_px_data[req_market].add(req_px)

            self._px_data_cache.data[req_px] = PxDataCacheEntryKeepUpdate(
                contract=None,
                period_sec=period_sec,
                contract_og=contract,
                data={},
                on_update=on_px_data_updated,
                on_update_market=on_market_data_received,
            )

            req_px_ids.append(req_px)

        return req_px_ids

    def is_all_px_data_ready(self, px_data_req_ids: list[int]) -> bool:
        return self._px_data_cache.is_all_px_data_ready(px_data_req_ids)
