import time

from trade_ibkr.const import IS_DEMO, SERVER_CONTRACTS
from trade_ibkr.obj import IBapiServer
from trade_ibkr.utils import make_futures_contract, print_log
from .handler import on_market_data_received, on_px_updated, register_handlers
from .socket import register_socket_endpoints


def run_ib_server(is_demo: bool | None = None, client_id: int | None = None) -> IBapiServer:
    is_demo = IS_DEMO if is_demo is None else is_demo

    app = IBapiServer()
    app.activate(
        8384 if is_demo else 8383,  # Configured at TWS
        client_id or (99 if is_demo else 1)
    )

    px_data_req_ids: list[int] = [
        req_id_same_contract for req_ids_cross_contract
        in [
            app.get_px_data_keep_update(
                contract=make_futures_contract(contract["symbol"], contract["exchange"]),
                duration=contract["duration"],
                bar_sizes=contract["bar-sizes"],
                period_secs=contract["period-secs"],
                on_px_data_updated=on_px_updated,
                on_market_data_received=on_market_data_received,
            ) for contract in SERVER_CONTRACTS
        ]
        for req_id_same_contract in req_ids_cross_contract
    ]

    while not app.is_all_px_data_ready(px_data_req_ids):
        time.sleep(0.25)
        print_log("[System] Waiting the initial data to ready")

    register_socket_endpoints(app, px_data_req_ids)
    register_handlers(app, px_data_req_ids)

    return app
