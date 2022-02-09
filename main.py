from trade_ibkr.const import fast_api, fast_api_socket
from trade_ibkr.enums import PxDataCol
from trade_ibkr.model import OnPxDataUpdatedEventNoAccount
from trade_ibkr.obj import start_app_info
from trade_ibkr.utils import make_futures_contract

fast_api = fast_api  # Binding for `uvicorn`

app, _ = start_app_info(is_demo=True)

contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")


# TODO: Show extrema of multiple contracts and S/R levels


async def on_px_updated(e: OnPxDataUpdatedEventNoAccount):
    await fast_api_socket.emit("pxUpdated", e.px_data.get_current()[PxDataCol.CLOSE])


@app.get_px_data_keep_update(contract=contract_mnq, duration="43200 S", bar_size="1 min")
async def on_all_px_data_received(e: OnPxDataUpdatedEventNoAccount):
    await on_px_updated(e)


@app.get_px_data_keep_update(contract=contract_mym, duration="43200 S", bar_size="1 min")
async def on_all_px_data_received(e: OnPxDataUpdatedEventNoAccount):
    await on_px_updated(e)
