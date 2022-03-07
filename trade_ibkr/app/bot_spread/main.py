import time
from decimal import Decimal

from trade_ibkr.const import IS_DEMO
from trade_ibkr.model import Commodity, CommodityPair
from trade_ibkr.obj import start_bot_spread, start_ib_server
from trade_ibkr.utils import make_futures_contract, print_log

from .socket import attach_socket
from .utils import get_spread


def run_bot_spread():
    app, _ = start_ib_server(is_demo=IS_DEMO, client_id=66)

    contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
    contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")

    async def px_updated(_):
        print("Px Updated")

    async def on_market_data_received(v):
        print("Market Px Updated")

    px_data_req_ids: list[int] = [
        req_id_same_contract for req_ids_cross_contract
        in [
            app.get_px_data_keep_update(
                contract=contract_mnq,
                duration="86400 S",
                bar_sizes=["1 min", "5 mins"],
                period_secs=[60, 300],
                on_px_data_updated=px_updated,
                on_market_data_received=on_market_data_received,
            ),
            app.get_px_data_keep_update(
                contract=contract_mym,
                duration="86400 S",
                bar_sizes=["1 min", "5 mins"],
                period_secs=[60, 300],
                on_px_data_updated=px_updated,
                on_market_data_received=on_market_data_received,
            ),
        ]
        for req_id_same_contract in req_ids_cross_contract
    ]

    while not app.is_all_px_data_ready(px_data_req_ids):
        time.sleep(0.25)
        print_log("[System] Waiting the initial data to ready")

    # register_socket_endpoints(app, px_data_req_ids)
    # register_handlers(app, px_data_req_ids)

    # contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
    # contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")

    # app, _ = start_bot_spread(
    #     commodity_pair=CommodityPair(
    #         buy_on_high=Commodity(contract=contract_mnq, quantity=Decimal(1)),
    #         buy_on_low=Commodity(contract=contract_mym, quantity=Decimal(3)),
    #         get_spread=get_spread,
    #     ),
    #     is_demo=IS_DEMO
    # )

    # attach_socket(app)
