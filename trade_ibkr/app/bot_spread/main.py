from decimal import Decimal

import numpy as np
from pandas import Series

from trade_ibkr.model import Commodity, CommodityPair, OnBotSpreadPxUpdatedEvent
from trade_ibkr.obj import IBautoBotSpread
from trade_ibkr.strategy import SpreadTradeParams, spread_trading_strategy
from trade_ibkr.utils import make_futures_contract


def get_spread(on_high: Series, on_low: Series) -> Series:
    return np.log(on_high.divide(on_low))


async def on_px_updated(e: OnBotSpreadPxUpdatedEvent):
    spread_trading_strategy(SpreadTradeParams(e=e))


def run_bot_spread():
    contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
    contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")

    app = IBautoBotSpread(
        commodity_pair=CommodityPair(
            buy_on_high=Commodity(contract=contract_mnq, quantity=Decimal(2)),
            buy_on_low=Commodity(contract=contract_mym, quantity=Decimal(6)),
            get_spread=get_spread,
        ),
        on_px_updated=on_px_updated,
    )
    app.activate(
        8384,  # Force demo
        77
    )
