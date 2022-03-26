from ibapi.contract import ContractDetails

from trade_ibkr.line import line_notify
from trade_ibkr.model import PxDataCache, PxDataCacheEntry
from trade_ibkr.utils import print_warning
from .components import IBapiOrderManagement, IBapiPnL


class IBapiServer(IBapiPnL, IBapiOrderManagement):
    def _on_px_data_updated(self, start_epoch: float, px_data_cache_entry: PxDataCacheEntry):
        super()._on_px_data_updated(start_epoch, px_data_cache_entry)

        if not line_notify.enabled or not self._px_data_cache.is_all_px_data_ready():
            print_warning("Attempted to report Px data but it is not fully ready")
            return

        line_notify.send_px_data_message(
            cache_entry.to_px_data() for cache_entry in self._px_data_cache.data.values()
        )

    def _init_get_px_data_cache(self) -> PxDataCache:
        return PxDataCache()

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)

        self.request_pnl_single(reqId, contractDetails)
