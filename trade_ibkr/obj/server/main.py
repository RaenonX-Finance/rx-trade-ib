from trade_ibkr.const import FORCE_STOP_LOSS_DIFF_SMA_X, FORCE_STOP_LOSS_PERIOD_SEC
from trade_ibkr.line import line_notify
from trade_ibkr.model import PxData, PxDataCache, PxDataCacheEntry
from trade_ibkr.utils import print_warning
from .components import IBapiOrderManagement, IBapiPx


class IBapiServer(IBapiPx, IBapiOrderManagement):
    def _on_px_data_updated(self, start_epoch: float, px_data_cache_entry: PxDataCacheEntry):
        super()._on_px_data_updated(start_epoch, px_data_cache_entry)

        if not line_notify.enabled or not self._px_data_cache.is_all_px_data_ready():
            print_warning("Attempted to report Px data but it is not fully ready")
            return

        px_data_list = [cache_entry.to_px_data() for cache_entry in self._px_data_cache.data.values()]

        line_notify.send_px_data_message(px_data_list)

        self._check_positions_force_stop_loss(px_data_list)

    def _check_positions_force_stop_loss(self, px_data_list: list[PxData]):
        px_data_dict: dict[int, PxData] = {
            px_data.contract_identifier: px_data for px_data in px_data_list
            if px_data.period_sec == FORCE_STOP_LOSS_PERIOD_SEC
        }

        if not self._position_data:
            print_warning("Position data not available, request position first")
            return

        for identifier, px_data in px_data_dict.items():
            position = self._position_data.get_position_data(identifier)

            if not position:
                continue

            diff_sma_x = float(position.px_diff(px_data.current_close)) / px_data.current_diff_sma
            if diff_sma_x < FORCE_STOP_LOSS_DIFF_SMA_X:
                print_warning(f"Force stop loss triggered @ Diff SMA {diff_sma_x:.3f}", force=True)

                self.cancel_open_orders_of_contract(px_data.contract)
                self.close_positions_of_contract(px_data.contract, position)

    def _init_get_px_data_cache(self) -> PxDataCache:
        return PxDataCache()
