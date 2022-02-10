from datetime import datetime

import uvicorn

from trade_ibkr.const import fast_api, fast_api_socket
from trade_ibkr.model import OnPxDataUpdatedEventNoAccount
from trade_ibkr.obj import start_app_info
from trade_ibkr.utils import make_futures_contract, make_crypto_contract, to_socket_message_px_data

fast_api = fast_api  # Binding for `uvicorn`

app, _ = start_app_info(is_demo=True)

contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")
contract_eth = make_crypto_contract("ETH")


# TODO: Show extrema of multiple contracts
# TODO: TA-lib pattern recognition?


async def on_px_updated(e: OnPxDataUpdatedEventNoAccount):
    print(f"{datetime.now().strftime('%H:%M:%S')}: Px Updated for {e.contract.underSymbol} ({e.proc_sec:.3f} s)")
    await fast_api_socket.emit("pxUpdated", to_socket_message_px_data(e.px_data))


@app.get_px_data_keep_update(contract=contract_mnq, duration="86400 S", bar_size="1 min")
async def on_mnq_px_data_received(e: OnPxDataUpdatedEventNoAccount):
    await on_px_updated(e)


@app.get_px_data_keep_update(contract=contract_mym, duration="86400 S", bar_size="1 min")
async def on_mym_px_data_received(e: OnPxDataUpdatedEventNoAccount):
    await on_px_updated(e)


if __name__ == "__main__":
    uvicorn.run("main:fast_api", host="127.0.0.1", port=5000)
