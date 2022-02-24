import asyncio
import time
from abc import ABC
from dataclasses import dataclass, field
from typing import TypeVar

from ibapi.common import BarData, TickAttrib, TickerId
from ibapi.contract import Contract, ContractDetails
from ibapi.ticktype import TickType, TickTypeEnum

from trade_ibkr.enums import PxDataCol
from trade_ibkr.model import (
    BarDataDict, OnMarketDataReceived, OnMarketDataReceivedEvent, OnPxDataUpdatedEventNoAccount,
    OnPxDataUpdatedNoAccount, PxData, to_bar_data_dict,
)
from .base import IBapiInfoBase


@dataclass(kw_only=True)
class PxDataCacheEntry(ABC):
    data: dict[int, BarDataDict]
    period_sec: int
    contract: ContractDetails | None
    contract_og: Contract
    on_update: OnPxDataUpdatedNoAccount

    last_historical_sent: float = field(init=False)
    last_market_update: float = field(init=False)

    def __post_init__(self):
        self.last_historical_sent = 0
        self.last_market_update = 0

    @property
    def is_ready(self) -> bool:
        return self.contract is not None and self.data

    @property
    def is_send_px_data_ok(self) -> bool:
        if not self.is_ready:
            return False

        # Debounce the data because `priceTick` and historical data update frequently
        return self.is_minute_changed_for_historical or time.time() - self.last_historical_sent > 3

    @property
    def is_send_market_px_data_ok(self) -> bool:
        # Limit market data output rate
        if not self.contract:
            return False

        return time.time() - self.last_market_update > 0.15

    @property
    def is_minute_changed_for_historical(self) -> bool:
        return int(self.last_historical_sent / 60) != int(time.time() / 60)

    @property
    def no_market_data_update(self) -> bool:
        # > 3 secs no incoming market data
        return time.time() - self.last_market_update > 3 and self.is_ready

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


@dataclass(kw_only=True)
class PxDataRequestParams:
    contract: Contract
    duration: str
    bar_size: str
    period_sec: int
    on_px_data_updated: OnPxDataUpdatedNoAccount


T = TypeVar("T", bound=PxDataCacheEntry)


class IBapiInfoPxData(IBapiInfoBase):
    def __init__(self):
        super().__init__()

        self._px_data_cache: dict[int, T] = {}
        self._px_data_complete: set[int] = set()
        self._px_req_id_to_contract_req_id: dict[int, int] = {}
        self._px_req_params: dict[int, PxDataRequestParams] = {}
        self._px_market_to_px_data: dict[int, int] = {}

    # region Historical Data

    def _on_historical_data_return(self, reqId: int, bar: BarData, /, remove_old: bool) -> bool:
        # If `bar.barCount` is -1, the data is incorrect
        if bar.barCount == -1:
            return False

        bar_data_dict = to_bar_data_dict(bar)
        epoch = bar_data_dict[PxDataCol.EPOCH_SEC]

        cache_entry = self._px_data_cache[reqId]
        cache_entry.data[bar_data_dict[PxDataCol.EPOCH_SEC]] = bar_data_dict

        is_new_bar = epoch not in cache_entry.data

        if is_new_bar and remove_old:
            # Keep price data in a fixed size
            cache_entry.data.pop(min(cache_entry.data.keys()))

        if contract_req_id := self._px_req_id_to_contract_req_id.get(reqId):
            # Add contract detail to PxData object
            cache_entry.contract = self._contract_data[contract_req_id]

        return is_new_bar

    @staticmethod
    def _trigger_on_px_data_updated(px_data_cache_entry: T):
        _time = time.time()

        async def execute_on_update():
            await px_data_cache_entry.on_update(OnPxDataUpdatedEventNoAccount(
                contract=px_data_cache_entry.contract,
                px_data=px_data_cache_entry.to_px_data(),
                proc_sec=time.time() - _time,
            ))

        asyncio.run(execute_on_update())

    def historicalData(self, reqId: int, bar: BarData):
        self._on_historical_data_return(reqId, bar, remove_old=False)

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        _time = time.time()
        self._on_historical_data_return(reqId, bar, remove_old=True)

        px_data_cache_entry = self._px_data_cache[reqId]

        if isinstance(px_data_cache_entry, PxDataCacheEntryKeepUpdate) and px_data_cache_entry.is_send_px_data_ok:
            self._trigger_on_px_data_updated(px_data_cache_entry)

        if px_data_cache_entry.no_market_data_update:
            # Re-trigger market data feed if stopped
            req_market = self._request_px_data_market(px_data_cache_entry.contract_og)
            self._px_market_to_px_data[req_market] = reqId

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        _time = time.time()
        px_data_cache_entry = self._px_data_cache[reqId]

        if px_data_cache_entry.is_send_px_data_ok:
            self._trigger_on_px_data_updated(px_data_cache_entry)

    # endregion

    # region Market Data

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        name = TickTypeEnum.idx2name[tickType]

        if name != "LAST":
            return

        px_data_cache_entry = self._px_data_cache[self._px_market_to_px_data[reqId]]

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

        px_data_cache_entry.last_market_update = time.time()

    # endregion

    def get_px_data_from_cache(self, req_id: int) -> PxData | None:
        px_data_entry = self._px_data_cache.get(req_id)

        if not px_data_entry:
            return None

        return px_data_entry.to_px_data()

    def _request_px_data(self, *, contract: Contract, duration: str, bar_size: str, keep_update: bool) -> int:
        request_id = self.next_valid_request_id

        self.reqHistoricalData(request_id, contract, "", duration, bar_size, "TRADES", 0, 2, keep_update, [])

        return request_id

    def _request_px_data_market(self, contract: Contract) -> int:
        request_id = self.next_valid_request_id

        self.reqMktData(request_id, contract, "", False, False, [])

        return request_id

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

        for bar_size, period_sec in zip(bar_sizes, period_secs):
            req_px = self._request_px_data(contract=contract, duration=duration, bar_size=bar_size, keep_update=True)
            req_contract = self._request_contract_data(contract)
            req_market = self._request_px_data_market(contract)
            self._px_req_id_to_contract_req_id[req_px] = req_contract
            self._px_market_to_px_data[req_market] = req_px

            self._px_data_cache[req_px] = PxDataCacheEntryKeepUpdate(
                contract=None,
                period_sec=period_sec,
                contract_og=contract,
                data={},
                on_update=on_px_data_updated,
                on_update_market=on_market_data_received,
            )

            req_px_ids.append(req_px)

        return req_px_ids
