import asyncio
import time
from abc import ABC
from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, TypeVar

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
    last_market_update: float | None = field(init=False)  # None means no data received yet

    def __post_init__(self):
        self.last_historical_sent = 0
        self.last_market_update = None

    @property
    def current_epoch_sec(self) -> int:
        return int(time.time()) // self.period_sec * self.period_sec

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

        if self.last_market_update is None:
            # First market data transmission
            return True

        return time.time() - self.last_market_update > 0.15

    @property
    def is_minute_changed_for_historical(self) -> bool:
        return int(self.last_historical_sent / 60) != int(time.time() / 60)

    @property
    def no_market_data_update(self) -> bool:
        # > 3 secs no incoming market data
        return (
                self.last_market_update is not None
                and time.time() - self.last_market_update > 3
                and self.is_ready
        )

    def to_px_data(self) -> PxData:
        self.last_historical_sent = time.time()

        return PxData(
            contract=self.contract,
            period_sec=self.period_sec,
            bars=[self.data[key] for key in sorted(self.data.keys())]
        )

    def remove_oldest(self):
        self.data.pop(min(self.data.keys()))

    def update_latest_market(self, current: float):
        self.last_market_update = time.time()

        epoch_latest = max(self.data.keys())
        epoch_current = self.current_epoch_sec

        if epoch_current > epoch_latest:
            # Current epoch is greater than the latest epoch
            new_bar: BarDataDict = {
                PxDataCol.OPEN: current,
                PxDataCol.HIGH: current,
                PxDataCol.LOW: current,
                PxDataCol.CLOSE: current,
                PxDataCol.EPOCH_SEC: epoch_current,
                PxDataCol.VOLUME: 0,
            }
            self.data[epoch_current] = new_bar
            self.remove_oldest()
            return

        bar_current = self.data[epoch_current]
        self.data[epoch_current] = bar_current | {
            PxDataCol.HIGH: max(bar_current[PxDataCol.HIGH], current),
            PxDataCol.LOW: min(bar_current[PxDataCol.LOW], current),
            PxDataCol.CLOSE: current,
        }

    def update_latest_history(self, bar: BarData, /, is_realtime_update: bool):
        # If `bar.barCount` is -1, the data is incorrect
        if bar.barCount == -1:
            return

        bar_data_dict = to_bar_data_dict(bar)

        epoch_to_rec = bar_data_dict[PxDataCol.EPOCH_SEC]
        epoch_current = self.current_epoch_sec

        if is_realtime_update and epoch_current > epoch_to_rec:
            # Epoch is newer, do nothing (let market update add the new bar)
            return

        self.data[epoch_to_rec] = bar_data_dict

        is_new_bar = epoch_to_rec not in self.data

        if is_new_bar and is_realtime_update:
            # Keep price data in a fixed size
            self.remove_oldest()


@dataclass(kw_only=True)
class PxDataCacheEntryOneTime(PxDataCacheEntry):
    pass


@dataclass(kw_only=True)
class PxDataCacheEntryKeepUpdate(PxDataCacheEntry):
    on_update_market: OnMarketDataReceived


T = TypeVar("T", bound=PxDataCacheEntry)


class IBapiInfoPxData(IBapiInfoBase):
    def __init__(self):
        super().__init__()

        self._px_data_cache: dict[int, T] = {}
        self._px_data_complete: set[int] = set()
        self._px_req_id_to_contract_req_id: dict[int, int] = {}
        self._px_market_to_px_data: DefaultDict[int, set[int]] = defaultdict(set)

    # region Historical Data

    def _on_historical_data_return(self, req_id_px: int, bar: BarData, /, is_realtime_update: bool):
        cache_entry = self._px_data_cache[req_id_px]

        if contract_req_id := self._px_req_id_to_contract_req_id.get(req_id_px):
            # Add contract detail to PxData object
            cache_entry.contract = self._contract_data[contract_req_id]

        cache_entry.update_latest_history(bar, is_realtime_update=is_realtime_update)

    @staticmethod
    def _on_px_data_updated(px_data_cache_entry: T):
        _time = time.time()

        async def execute_on_update():
            await px_data_cache_entry.on_update(OnPxDataUpdatedEventNoAccount(
                contract=px_data_cache_entry.contract,
                px_data=px_data_cache_entry.to_px_data(),
                proc_sec=time.time() - _time,
            ))

        asyncio.run(execute_on_update())

    def historicalData(self, reqId: int, bar: BarData):
        self._on_historical_data_return(reqId, bar, is_realtime_update=False)

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        _time = time.time()
        self._on_historical_data_return(reqId, bar, is_realtime_update=True)

        px_data_cache_entry = self._px_data_cache[reqId]

        if isinstance(px_data_cache_entry, PxDataCacheEntryKeepUpdate) and px_data_cache_entry.is_send_px_data_ok:
            self._on_px_data_updated(px_data_cache_entry)

        if px_data_cache_entry.no_market_data_update:
            # Re-trigger market data feed if stopped
            req_market = self._request_px_data_market(px_data_cache_entry.contract_og)
            self._px_market_to_px_data[req_market].add(reqId)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        _time = time.time()
        px_data_cache_entry = self._px_data_cache[reqId]

        if px_data_cache_entry.is_send_px_data_ok:
            self._on_px_data_updated(px_data_cache_entry)

    # endregion

    # region Market Data

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        name = TickTypeEnum.idx2name[tickType]

        if name != "LAST":
            return

        on_update_executed = False

        for px_req_id in self._px_market_to_px_data[reqId]:
            px_data_cache_entry = self._px_data_cache[px_req_id]

            if (
                    not isinstance(px_data_cache_entry, PxDataCacheEntryKeepUpdate) or
                    not px_data_cache_entry.is_send_market_px_data_ok
            ):
                return

            if not on_update_executed:
                on_update_executed = True

                async def execute_on_update():
                    await px_data_cache_entry.on_update_market(OnMarketDataReceivedEvent(
                        contract=px_data_cache_entry.contract,
                        px=price,
                    ))

                asyncio.run(execute_on_update())

            px_data_cache_entry.update_latest_market(price)

    # endregion

    def is_all_px_data_ready(self, px_data_req_ids: list[int]) -> bool:
        return all(self._px_data_cache[px_data_req_id].is_ready for px_data_req_id in px_data_req_ids)

    def get_px_data_from_cache(self, req_id: int) -> PxData:
        px_data_entry = self._px_data_cache[req_id]
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

        req_contract = self._request_contract_data(contract)
        req_market = self._request_px_data_market(contract)

        for bar_size, period_sec in zip(bar_sizes, period_secs):
            req_px = self._request_px_data(contract=contract, duration=duration, bar_size=bar_size, keep_update=True)
            self._px_req_id_to_contract_req_id[req_px] = req_contract
            self._px_market_to_px_data[req_market].add(req_px)

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
