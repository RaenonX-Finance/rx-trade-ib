import asyncio
from dataclasses import dataclass
from typing import Callable, ParamSpec, TypeVar

from ibapi.client import EClient
from ibapi.common import BarData
from ibapi.contract import Contract, ContractDetails
from ibapi.wrapper import EWrapper

from trade_ibkr.enums import PxDataCol
from trade_ibkr.model import (
    BarDataDict, OnPxDataUpdatedNoAccount, OnPxDataUpdatedEventNoAccount, PxData,
    to_bar_data_dict,
)

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(kw_only=True)
class PxDataCacheEntry:
    data: dict[int, BarDataDict]
    contract: Contract
    on_update: OnPxDataUpdatedNoAccount

    def to_px_data(self) -> PxData:
        return PxData(contract=self.contract, bars=[self.data[key] for key in sorted(self.data.keys())])


class IBapiInfo(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

        self._px_data_cache: dict[int, PxDataCacheEntry] = {}
        self._px_data_complete: set[int] = set()
        self._px_req_id_to_contract_req_id: dict[int, int] = {}

        self._contract_data: dict[int, Contract | None] = {}

        self._order_id = 0
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
        self._contract_data[reqId] = contractDetails.contract

    # endregion

    # region Historical Data

    def _on_historical_data_return(self, reqId: int, bar: BarData, /, remove_old: bool):
        # If `bar.barCount` is -1, the data is incorrect
        if bar.barCount == -1:
            return

        bar_data_dict = to_bar_data_dict(bar)

        cache_entry = self._px_data_cache[reqId]
        cache_entry.data[bar_data_dict[PxDataCol.EPOCH_SEC]] = bar_data_dict

        if remove_old:
            cache_entry.data.pop(min(cache_entry.data.keys()))

    def historicalData(self, reqId: int, bar: BarData):
        self._on_historical_data_return(reqId, bar, remove_old=False)

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        self._on_historical_data_return(reqId, bar, remove_old=True)

        async def execute_on_update():
            await self._px_data_cache[reqId].on_update(OnPxDataUpdatedEventNoAccount(
                contract=self._contract_data[self._px_req_id_to_contract_req_id[reqId]],
                px_data=self._px_data_cache[reqId].to_px_data(),
            ))

        asyncio.run(execute_on_update())

    def request_px_data(self, *, contract: Contract, duration: str, bar_size: str, keep_update: bool) -> int:
        request_id = self.next_valid_request_id

        self.reqHistoricalData(request_id, contract, "", duration, bar_size, "TRADES", 0, 2, keep_update, [])

        return request_id

    def get_px_data_keep_update(
            self, *,
            contract: Contract, duration: str, bar_size: str,
    ) -> Callable[[OnPxDataUpdatedNoAccount], None]:
        req_px = self.request_px_data(contract=contract, duration=duration, bar_size=bar_size, keep_update=True)
        req_contract = self.request_contract_data(contract)
        self._px_req_id_to_contract_req_id[req_px] = req_contract

        def decorator(on_all_px_data_received: OnPxDataUpdatedNoAccount):
            self._px_data_cache[req_px] = PxDataCacheEntry(
                contract=contract,
                data={},
                on_update=on_all_px_data_received,
            )

        return decorator

    # endregion
