from trade_ibkr.obj import start_app_info
from trade_ibkr.utils import make_futures_contract
from .handler import on_market_data_received, on_px_updated, register_handlers
from .socket import register_socket_endpoints


def prepare_info_app():
    app, _ = start_app_info(is_demo=True)

    contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
    contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")
    # contract_eth = make_crypto_contract("ETH")

    px_data_req_ids: list[int] = [
        req_id for req_ids in [
            app.get_px_data_keep_update(
                contract=contract_mnq,
                duration="3 D",
                bar_sizes=["1 min", "5 mins"],
                period_secs=[60, 300],
                on_px_data_updated=on_px_updated,
                on_market_data_received=on_market_data_received,
            ),
            app.get_px_data_keep_update(
                contract=contract_mym,
                duration="3 D",
                bar_sizes=["1 min", "5 mins"],
                period_secs=[60, 300],
                on_px_data_updated=on_px_updated,
                on_market_data_received=on_market_data_received,
            ),
        ] for req_id in req_ids
    ]

    register_socket_endpoints(app, px_data_req_ids)
    register_handlers(app, px_data_req_ids)
