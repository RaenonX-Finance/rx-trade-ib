from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from ibapi.client import EClient
from ibapi.common import BarData
from ibapi.contract import Contract, ContractDetails
from ibapi.wrapper import EWrapper

from trade_ibkr.enums import FetchStatus, PxDataCol
from trade_ibkr.model import (
    BacktestAccount, BarDataDict, OnPxDataUpdated, OnPxDataUpdatedEvent, Position, PositionData, PxData,
    to_bar_data_dict,
)


@dataclass(kw_only=True)
class PxDataCacheEntry:
    data: dict[int, BarDataDict]
    on_update: OnPxDataUpdated | None
    contract: ContractDetails | None

    def to_px_data(self) -> PxData:
        return PxData(contract=self.contract, bars=[self.data[key] for key in sorted(self.data.keys())])


class IBapiBacktest(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

        self._px_data_cache: dict[int, PxDataCacheEntry] = {}
        self._px_data_complete: set[int] = set()

        self._position_data_list: list[PositionData] = []
        self._position_data_fetch_status: FetchStatus = FetchStatus.NOT_FETCHED

        self._position_data: Position | None = None

        self._contract_data: dict[int, ContractDetails | None] = {}

        self._request_id = -1

    @property
    def next_valid_request_id(self) -> int:
        self._request_id += 1

        return self._request_id

    # region Contract

    def request_contract_data(self, contract: Contract) -> int:
        request_id = self.next_valid_request_id

        self.reqContractDetails(request_id, contract)

        return request_id

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        self._contract_data[reqId] = contractDetails

    # endregion

    # region Historical Data

    def _on_historical_data_return(self, reqId: int, bar: BarData, /, remove_old: bool) -> bool:
        # If `bar.barCount` is -1, the data is incorrect
        if bar.barCount == -1:
            return False

        bar_data_dict = to_bar_data_dict(bar)
        epoch = bar_data_dict[PxDataCol.EPOCH_SEC]

        cache_entry = self._px_data_cache[reqId]

        is_new_bar = epoch not in cache_entry.data

        cache_entry.data[epoch] = bar_data_dict

        if is_new_bar and remove_old:
            cache_entry.data.pop(min(cache_entry.data.keys()))

        return is_new_bar

    def historicalData(self, reqId: int, bar: BarData):
        self._on_historical_data_return(reqId, bar, remove_old=False)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        self._px_data_complete.add(reqId)

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        is_new_bar = self._on_historical_data_return(reqId, bar, remove_old=True)

        cache_entry = self._px_data_cache[reqId]

        if not cache_entry.on_update:
            return

        cache_entry.on_update(OnPxDataUpdatedEvent(
            px_data=cache_entry.to_px_data(),
            account=BacktestAccount(),
            contract=cache_entry.contract.contract,
            is_new_bar=is_new_bar,
        ))

    def request_px_data(
            self, *,
            contract: Contract,
            duration: str,
            bar_size: str,
            on_px_data_updated: OnPxDataUpdated | None = None
    ) -> int:
        request_id = self.next_valid_request_id

        self._px_data_cache[request_id] = PxDataCacheEntry(
            on_update=on_px_data_updated,
            contract=None,
            data={},
        )

        self.reqHistoricalData(request_id, contract, "", duration, bar_size, "TRADES", 0, 2, True, [])

        return request_id

    def trade_on_px_data_backtest(
            self, *,
            account: BacktestAccount,
            contract: Contract,
            duration: str,
            bar_size: str,
            min_data_rows: int,
    ) -> Callable[[OnPxDataUpdated], None]:
        req_id_px = self.request_px_data(contract=contract, duration=duration, bar_size=bar_size)
        req_id_contract = self.request_contract_data(contract)

        while req_id_px not in self._px_data_complete or req_id_contract not in self._contract_data:
            time.sleep(0.1)

        px_data = self._px_data_cache[req_id_px].to_px_data()
        px_data.dataframe.to_csv("data.csv")

        def decorator(on_px_data_updated: OnPxDataUpdated) -> None:
            for df, is_new_bar in px_data.get_dataframes_backtest(min_data_rows=min_data_rows):
                contract_fetched = self._contract_data[req_id_contract]

                event = OnPxDataUpdatedEvent(
                    px_data=PxData(contract=contract_fetched, dataframe=df),
                    account=account,
                    contract=contract_fetched.contract,
                    is_new_bar=is_new_bar,
                )

                on_px_data_updated(event)

        return decorator

    # endregion
