from dataclasses import dataclass

from .client import GetSpread
from .px_data_cache import PxDataCache, PxDataCacheEntry
from .px_data_pair import PxDataPair
from .unrlzd_pnl import UnrealizedPnL


@dataclass(kw_only=True)
class PxDataPairCacheEntry(PxDataCacheEntry):
    unrlzd_pnl: UnrealizedPnL


@dataclass(kw_only=True)
class PxDataPairCache(PxDataCache[PxDataPairCacheEntry]):
    px_req_id_high: int | None = None
    px_req_id_low: int | None = None

    def is_data_ready(self) -> bool:
        return all(data_of_single_commodity.data for data_of_single_commodity in self.data.values())

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
