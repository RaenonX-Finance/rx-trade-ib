import time

from trade_ibkr.const import IS_DEMO, SERVER_CLIENT_ID_DEMO, SERVER_CLIENT_ID_LIVE, SERVER_CONTRACTS
from trade_ibkr.obj import IBapiServer
from trade_ibkr.utils import print_log, ContractParams, TYPE_TO_CONTRACT_FUNCTION, print_warning
from .handler import on_market_data_received, on_px_updated, register_handlers
from .socket import register_socket_endpoints


def run_ib_server(is_demo: bool | None = None, client_id: int | None = None) -> IBapiServer:
    is_demo = IS_DEMO if is_demo is None else is_demo

    app = IBapiServer()
    app.activate(
        8384 if is_demo else 8383,  # Configured at TWS
        client_id or (SERVER_CLIENT_ID_LIVE if is_demo else SERVER_CLIENT_ID_DEMO)
    )

    px_data_req_ids: list[int] = []

    for contract in SERVER_CONTRACTS:
        for contract_data in contract["data"]:
            contract_params = ContractParams(
                symbol=contract["symbol"],
                exchange=contract["exchange"],
                type_=contract["type"],
            )

            if not contract_data.get("enable", True):
                print_warning(f"Skipping contract creation of {contract_params} as it is not enabled")

            contract_maker = TYPE_TO_CONTRACT_FUNCTION.get(contract_params.type_)

            if not contract_maker:
                raise ValueError(f"Contract {contract_params} do not have corresponding maker function")

            px_data_req_ids.append(app.get_px_data_keep_update(
                contract=contract_maker(contract_params),
                duration=contract_data["duration"],
                bar_size=contract_data["bar-size"],
                period_sec=contract_data["period-secs"],
                is_major=contract_data.get("is-major", False),
                on_px_data_updated=on_px_updated,
                on_market_data_received=on_market_data_received,
            ))

    while not app.is_all_px_data_ready(px_data_req_ids):
        time.sleep(0.25)
        print_log("[System] Waiting the initial data to ready")

    register_socket_endpoints(app, px_data_req_ids)
    register_handlers(app, px_data_req_ids)

    return app
