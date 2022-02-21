from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.calc import has_continuous_2_extrema
from trade_ibkr.enums import PxDataCol
from trade_ibkr.model import PxData, Account


def _stop_loss(*, account: Account, contract: Contract, px_data: PxData, desired_px: float):
    if not (position_data := account.get_current_position_data(contract)):
        return

    candle_current = px_data.get_current()

    px_diff = position_data.px_diff(candle_current[PxDataCol.CLOSE])

    # Amplitude-adjusted stop-loss
    tolerance = candle_current[PxDataCol.AMPLITUDE_HL] * 1.5

    if px_diff * position_data.side.multiplier < 0 and abs(px_diff) > tolerance:
        print(f"SL - Over tolerance @ {desired_px}")
        account.exit(contract, desired_px)
        return


def _take_profit(*, account: Account, contract: Contract, px_data: PxData, desired_px: float):
    position_data = account.get_current_position_data(contract)

    if not position_data:
        # No position
        return

    candle_current = px_data.get_current()
    candle_prev = px_data.get_last_n(2)

    position_side = account.get_current_position_side(contract)

    candle_current = px_data.get_current()

    px_diff = position_data.px_diff(candle_current[PxDataCol.CLOSE])

    # TODO: 1/2 Profit guarantee

    # Amplitude-adjusted take-profit
    amplitude_coeff = candle_current[PxDataCol.AMPLITUDE_HL] * 4

    if px_diff * position_data.side.multiplier > 0 and abs(px_diff) > amplitude_coeff:
        print(f"TP - Over tolerance @ {desired_px}")
        account.exit(contract, desired_px)
        return


def _enter(
        *,
        account: Account, contract: Contract, px_data: PxData, desired_px: float, quantity: Decimal,
):
    candle_current = px_data.get_current()

    support_resistance_threshold = 100

    if has_continuous_2_extrema(px_data, PxDataCol.LOCAL_MIN, PxDataCol.LOCAL_MAX, limit_count=5):
        account.short(contract, quantity, desired_px, f"ET - Double top SHORT @ {desired_px}")
    elif has_continuous_2_extrema(px_data, PxDataCol.LOCAL_MAX, PxDataCol.LOCAL_MIN, limit_count=5):
        account.long(contract, quantity, desired_px, f"ET - Double top LONG @ {desired_px}")
    elif px_data.get_px_sr_score(candle_current[PxDataCol.CLOSE]):
        account.short(contract, quantity, desired_px)
        account.long(contract, quantity, desired_px)


def simple_strategy(
        contract: Contract, account: Account, px_data: PxData,
        /, attempt_enter: bool, quantity: Decimal,
):
    candle_current = px_data.get_current()
    current_side = account.get_current_position_side(contract)
    desired_px = candle_current[PxDataCol.CLOSE] - 1.5 * current_side.multiplier

    if account.action_status.order_pending:
        # Prevent duplicated orders
        return

    _take_profit(account=account, contract=contract, px_data=px_data, desired_px=desired_px)

    # TODO: Exit & No Enter @ 14:57 / 15:57
    # TODO: N pattern detection
    # TODO: Exit at last optima
    # TODO: Self back test - record reason and check PNL
    # TODO: Support / Resistance
    #   - Exit if 3 Ks staying around the same
    #   - https://medium.datadriveninvestor.com/how-to-detect-support-resistance-levels-and-breakout-using-python-f8b5dac42f21
    #   - https://medium.com/@craigmariani47/building-a-stock-trading-bot-in-python-8be56bf5fe0d

    if attempt_enter and not account.action_status.order_executed_on_current_k:
        _enter(
            account=account, contract=contract, px_data=px_data,
            desired_px=desired_px, quantity=quantity,
        )

    _stop_loss(
        account=account, contract=contract,
        px_data=px_data, desired_px=desired_px,
    )
