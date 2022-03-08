from trade_ibkr.model import PxDataCache
from .components import IBapiPx, IBapiOrderManagement


class IBapiServer(IBapiPx, IBapiOrderManagement):
    def _init_get_px_data_cache(self) -> PxDataCache:
        return PxDataCache()
