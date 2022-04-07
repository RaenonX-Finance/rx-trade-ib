import time
from abc import ABC
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Generic, TypeVar

from ibapi.common import BarData
from ibapi.contract import Contract, ContractDetails

from trade_ibkr.const import UPDATE_FREQ_HST_PX, UPDATE_FREQ_MKT_PX
from trade_ibkr.enums import PxDataCol
from .bar_data import BarDataDict, to_bar_data_dict
from .px_data import PxData
from .server import OnPxDataUpdatedNoAccount


@dataclass(kw_only=True)
class PxDataCacheEntry(ABC):
    data: dict[int, BarDataDict]
    period_sec: int
    is_major: bool
    contract: ContractDetails | None
    contract_og: Contract

    on_update: OnPxDataUpdatedNoAccount | None

    last_historical_sent: float = field(init=False)
    last_market_update: float | None = field(init=False)  # None means no data received yet

    def __post_init__(self):
        self.last_historical_sent = 0
        self.last_market_update = None

    @property
    def current_epoch_sec(self) -> int:
        # Epoch sec is YYYYMMDD instead for daily bar
        if self.period_sec >= 86400:
            today = date.today()

            return int(datetime(today.year, today.month, today.day).timestamp())

        return int(time.time()) // self.period_sec * self.period_sec

    @property
    def is_ready(self) -> bool:
        return self.contract is not None and self.data

    @property
    def is_send_px_data_ok(self) -> bool:
        if not self.is_ready:
            return False

        # Debounce the data because `priceTick` and historical data update frequently
        return (
                self.is_minute_changed_for_historical
                or time.time() - self.last_historical_sent > UPDATE_FREQ_HST_PX
        )

    @property
    def is_send_market_px_data_ok(self) -> bool:
        # Limit market data output rate
        if not self.contract:
            return False

        if self.last_market_update is None:
            # First market data transmission
            return True

        return time.time() - self.last_market_update > UPDATE_FREQ_MKT_PX

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

    def remove_oldest(self):
        self.data.pop(min(self.data.keys()))

    def update_latest_market(self, current: float):
        self.last_market_update = time.time()

        epoch_latest = max(self.data.keys()) if self.data else 0
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

        bar_data_dict = to_bar_data_dict(bar, is_date_ymd=self.period_sec >= 86400)

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

    def to_px_data(self) -> PxData:
        self.last_historical_sent = time.time()

        return PxData(
            contract=self.contract,
            period_sec=self.period_sec,
            is_major=self.is_major,
            bars=[self.data[key] for key in sorted(self.data.keys())]
        )


E = TypeVar("E", bound=PxDataCacheEntry)


@dataclass(kw_only=True)
class PxDataCache(Generic[E]):
    data: dict[int, E] = field(init=False)

    def __post_init__(self):
        self.data = {}

    def is_all_px_data_ready(self) -> bool:
        return all(px_data_entry.is_ready for px_data_entry in self.data.values())
