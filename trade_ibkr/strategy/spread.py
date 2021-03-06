from dataclasses import dataclass
from datetime import datetime, time

from pandas import Series

from trade_ibkr.enums import PxDataPairCol, Side
from trade_ibkr.model import Account, CommodityPair, OnBotSpreadPxUpdatedEvent, UnrealizedPnL
from trade_ibkr.utils import get_basic_contract_symbol, get_contract_identifier, print_log


@dataclass(kw_only=True)
class SpreadTradeParams:
    e: OnBotSpreadPxUpdatedEvent

    @property
    def last_px(self) -> Series:
        return self.e.px_data_pair.get_last()

    @property
    def on_high(self):
        return self.e.commodity_pair.buy_on_high

    @property
    def on_low(self):
        return self.e.commodity_pair.buy_on_low

    @property
    def commodity_pair(self) -> CommodityPair:
        return self.e.commodity_pair

    @property
    def account(self) -> Account:
        return self.e.account

    @property
    def unrlzd_pnl(self) -> UnrealizedPnL:
        return self.e.unrlzd_pnl

    @property
    def has_pending_order(self) -> bool:
        return self.e.has_pending_order


def _is_good_entry_time() -> bool:
    # Allow entry from 2:30 CST / 3:30 CDT (8:30 UTC) to 6:30 CST / 7:30 CDT (12:30 UTC)
    return time(8, 30) <= datetime.utcnow().time() < time(12, 30)


def _is_allowed_to_enter(params: SpreadTradeParams) -> bool:
    return _is_good_entry_time() and not params.has_pending_order


def _has_open_position(params: SpreadTradeParams) -> bool:
    for commodity in params.commodity_pair.commodities:
        if params.account.get_current_position_side(get_contract_identifier(commodity.contract)) != Side.NEUTRAL:
            return True

    return False


def _util_exit_all(params: SpreadTradeParams, message: str):
    for commodity in params.commodity_pair.commodities:
        try:
            params.account.exit(contract=commodity.contract, message=message)
        except ValueError:
            # No order side - already exited
            pass


def _entry_out_of_band(params: SpreadTradeParams):
    spread = params.last_px[PxDataPairCol.SPREAD]
    spread_hi = params.last_px[PxDataPairCol.SPREAD_HI]
    spread_lo = params.last_px[PxDataPairCol.SPREAD_LO]

    spread_diff = spread_hi - spread_lo
    spread_loc = (spread - spread_lo) / spread_diff

    print_log(
        f"[BOT - Spread] Checking entry | "
        f"{spread:.6f} | "
        f"HI - {1 - spread_loc:.2%} - CUR - {spread_loc:.2%} - LO"
    )

    if spread > spread_hi:
        params.account.long(
            params.on_high.contract, params.on_high.quantity, px=None,
            message=f"ENTRY: Buy on out of BB (high) - {get_basic_contract_symbol(params.on_high.contract)}"
        )
        params.account.short(
            params.on_low.contract, params.on_low.quantity, px=None,
            message=f"ENTRY: Buy on out of BB (high) - {get_basic_contract_symbol(params.on_high.contract)}"
        )
        return

    if spread < spread_lo:
        params.account.long(
            params.on_low.contract, params.on_low.quantity, px=None,
            message=f"ENTRY: Buy on out of BB (low) - {get_basic_contract_symbol(params.on_high.contract)}"
        )
        params.account.short(
            params.on_high.contract, params.on_high.quantity, px=None,
            message=f"ENTRY: Buy on out of BB (low) - {get_basic_contract_symbol(params.on_high.contract)}"
        )
        return


def _exit_force_no_cross_day_position(params: SpreadTradeParams):
    current_utc_time = datetime.utcnow().time()

    if (current_utc_time.hour, current_utc_time.minute) != (12, 30):
        return

    # Force exit at 6:30 CST / 7:30 CDT (12:30 UTC)
    _util_exit_all(params, "EXIT - FORCE: Out of allowed trading timeframe")


def _exit_take_profit_back_to_mid(params: SpreadTradeParams):
    spread = params.last_px[PxDataPairCol.SPREAD]
    spread_mid = params.last_px[PxDataPairCol.SPREAD_MID]

    spread_diff = params.last_px[PxDataPairCol.SPREAD_HI] - spread_mid
    spread_loc = (spread - spread_mid) / spread_diff

    on_high_side = params.account.get_current_position_side(get_contract_identifier(params.on_high.contract))

    print_log(
        f"[BOT - Spread] Checking exit - Current @ {spread_loc:.2%} (100% - 0%) | "
        f"{spread:.6f} | High Side: {on_high_side}"
    )

    if on_high_side == Side.LONG and spread < spread_mid:
        _util_exit_all(params, "EXIT - PROFIT: Back to BB mid (high)")

    if on_high_side == Side.SHORT and spread > spread_mid:
        _util_exit_all(params, "EXIT - PROFIT: Back to BB mid (low)")


def _exit_take_profit_lock_profit(params: SpreadTradeParams):
    if params.unrlzd_pnl.current < 10 and params.unrlzd_pnl.max > 40:
        _util_exit_all(params, "EXIT - PROFIT: Lock profit")


def _exit_stop_loss_force(params: SpreadTradeParams):
    if params.unrlzd_pnl.current < -50:
        _util_exit_all(params, "EXIT - STOP LOSS: Unrealized PnL < -50")


def spread_trading_strategy(params: SpreadTradeParams):
    _exit_force_no_cross_day_position(params)

    # Only attempt to enter at :00
    if datetime.now().second == 0:
        if not _is_allowed_to_enter(params):
            print_log(f"[BOT - Spread] Not allowed to enter - Has pending order: {params.has_pending_order}")
            return

        _entry_out_of_band(params)

    has_open_position = _has_open_position(params)

    if has_open_position:
        _exit_take_profit_back_to_mid(params)
        _exit_take_profit_lock_profit(params)
        _exit_stop_loss_force(params)
        return
