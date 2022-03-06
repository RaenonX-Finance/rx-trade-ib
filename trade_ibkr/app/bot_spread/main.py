from decimal import Decimal

import numpy as np
from pandas import Series

from trade_ibkr.const import IS_DEMO
from trade_ibkr.model import Commodity, CommodityPair, OnMarketPxUpdatedOfBotSpreadEvent
from trade_ibkr.obj import start_app_bot_spread
from trade_ibkr.strategy import spread_trading_strategy
from trade_ibkr.strategy.spread import SpreadTradeParams
from trade_ibkr.utils import make_futures_contract, print_log


def get_spread(on_high: Series, on_low: Series) -> Series:
    # On Low = MYM - On High = MNQ
    # MYM / MNQ gives the correct result
    return np.log(on_low.divide(on_high))


async def on_px_updated(e: OnMarketPxUpdatedOfBotSpreadEvent):
    print_log(f"[TWS] Px Updated - ({e})")
    spread_trading_strategy(SpreadTradeParams(e=e))


def prepare_bot_app_spread():
    contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
    contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")

    app, _ = start_app_bot_spread(
        commodity_pair=CommodityPair(
            buy_on_high=Commodity(contract=contract_mnq, quantity=Decimal(1)),
            buy_on_low=Commodity(contract=contract_mym, quantity=Decimal(3)),
            get_spread=get_spread,
        ),
        on_px_updated=on_px_updated,
        is_demo=IS_DEMO
    )
