from trade_ibkr.line import line_notify
from trade_ibkr.model import PxDataCache, PxDataCacheEntry
from trade_ibkr.utils import print_warning
from .components import IBapiOrderManagement, IBapiPx


class IBapiServer(IBapiPx, IBapiOrderManagement):
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
