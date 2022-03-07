from decimal import Decimal

from trade_ibkr.const import IS_DEMO
from trade_ibkr.model import Commodity, CommodityPair
from trade_ibkr.obj import start_bot_spread
from trade_ibkr.utils import make_futures_contract

from .socket import attach_socket
from .utils import get_spread


def prepare_bot_app_spread():
    contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
    contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")

    app, _ = start_bot_spread(
        commodity_pair=CommodityPair(
            buy_on_high=Commodity(contract=contract_mnq, quantity=Decimal(1)),
            buy_on_low=Commodity(contract=contract_mym, quantity=Decimal(3)),
            get_spread=get_spread,
        ),
        is_demo=IS_DEMO
    )

    # attach_socket(app)
