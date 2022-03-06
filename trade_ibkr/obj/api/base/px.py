from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable, DefaultDict, Generic, TypeVar

from ibapi.common import BarData, TickAttrib, TickerId
from ibapi.contract import Contract
from ibapi.ticktype import TickType, TickTypeEnum

from trade_ibkr.model import PxDataCacheBase, PxDataCacheEntryBase
from .contract import IBapiBaseContract

E = TypeVar("E", bound=PxDataCacheEntryBase)
T = TypeVar("T", bound=PxDataCacheBase)


class IBapiBasePx(Generic[E, T], IBapiBaseContract, ABC):
    @abstractmethod
    def _init_px_data_cache(self) -> T:
        raise NotImplementedError()

    def __init__(self):
        super().__init__()

        self._px_data_cache: T = self._init_px_data_cache()
        self._px_req_id_to_contract_req_id: dict[int, int] = {}
        self._px_market_to_px_data: DefaultDict[int, set[int]] = defaultdict(set)
        self._contract_req_id_to_px_req_id: DefaultDict[int, set[int]] = defaultdict(set)

    # region Historical Data

    def _on_historical_data_return(self, req_id_px: int, bar: BarData, /, is_realtime_update: bool):
        cache_entry = self._px_data_cache.data[req_id_px]

        if contract_req_id := self._px_req_id_to_contract_req_id.get(req_id_px):
            # Add contract detail to PxData object
            cache_entry.contract = self._contract_data[contract_req_id]

        cache_entry.update_latest_history(bar, is_realtime_update=is_realtime_update)

    def historicalData(self, reqId: int, bar: BarData):
        super().historicalData(reqId, bar)

        self._on_historical_data_return(reqId, bar, is_realtime_update=False)

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        super().historicalDataUpdate(reqId, bar)

        self._on_historical_data_return(reqId, bar, is_realtime_update=True)

        px_data_cache_entry = self._px_data_cache.data[reqId]

        if px_data_cache_entry.no_market_data_update:
            # Re-trigger market data feed if stopped
            req_market = self._request_px_data_market(px_data_cache_entry.contract_og)
            self._px_market_to_px_data[req_market].add(reqId)

    def _request_px_data(self, *, contract: Contract, duration: str, bar_size: str, keep_update: bool) -> int:
        request_id = self.next_valid_request_id

        self.reqHistoricalData(request_id, contract, "", duration, bar_size, "TRADES", 0, 2, keep_update, [])

        return request_id

    # endregion

    # region Market Data

    @abstractmethod
    def on_market_px_updated(self, px_req_id: int, px: float):
        raise NotImplementedError()

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        name = TickTypeEnum.idx2name[tickType]

        if name != "LAST":
            return

        px_req_id = next(px_req_id for px_req_id in self._px_market_to_px_data[reqId])

        self._px_data_cache.data[px_req_id].update_latest_market(price)
        self.on_market_px_updated(px_req_id, price)

    def _request_px_data_market(self, contract: Contract) -> int:
        request_id = self.next_valid_request_id

        self.reqMktData(request_id, contract, "", False, False, [])

        return request_id

    # endregion

    def _get_px_data_keep_update(
            self, *,
            contract: Contract, duration: str, bar_sizes: list[str], period_secs: list[int],
            get_new_cache_entry: Callable[[int], E],
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

            self._px_data_cache.data[req_px] = get_new_cache_entry(period_sec)

            req_px_ids.append(req_px)

        return req_px_ids
