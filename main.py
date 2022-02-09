from trade_ibkr.const import fast_api, fast_api_socket
from trade_ibkr.model import OnPxDataUpdatedEventNoAccount
from trade_ibkr.obj import start_app_info
from trade_ibkr.utils import make_futures_contract, make_crypto_contract, to_socket_message_px_data

fast_api = fast_api  # Binding for `uvicorn`

app, _ = start_app_info(is_demo=True)

contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")
contract_eth = make_crypto_contract("ETH")


# TODO: Show extrema of multiple contracts and S/R levels


async def on_px_updated(e: OnPxDataUpdatedEventNoAccount):
    await fast_api_socket.emit("pxUpdated", to_socket_message_px_data(e.px_data))


@app.get_px_data_keep_update(contract=contract_mnq, duration="43200 S", bar_size="1 min")
async def on_mnq_px_data_received(e: OnPxDataUpdatedEventNoAccount):
    await on_px_updated(e)


@app.get_px_data_keep_update(contract=contract_eth, duration="1800 S", bar_size="1 min")
async def on_eth_px_data_received(e: OnPxDataUpdatedEventNoAccount):
    await on_px_updated(e)


@app.get_px_data_keep_update(contract=contract_mym, duration="43200 S", bar_size="1 min")
async def on_mym_px_data_received(e: OnPxDataUpdatedEventNoAccount):
    await on_px_updated(e)
