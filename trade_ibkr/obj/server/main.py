from ibapi.contract import ContractDetails

from trade_ibkr.model import PxDataCache
from .components import IBapiOrderManagement, IBapiPnL


class IBapiServer(IBapiPnL, IBapiOrderManagement):
    def _init_get_px_data_cache(self) -> PxDataCache:
        return PxDataCache()

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)

        self.request_pnl_single(reqId, contractDetails)
