from datetime import datetime

import uvicorn

from trade_ibkr.const import fast_api, fast_api_socket
from trade_ibkr.model import OnPxDataUpdatedEventNoAccount, OnMarketDataReceivedEvent
from trade_ibkr.obj import start_app_info
from trade_ibkr.utils import (
    make_futures_contract, make_crypto_contract,
    to_socket_message_px_data, to_socket_message_px_data_market,
)

fast_api = fast_api  # Binding for `uvicorn`

app, _ = start_app_info(is_demo=True)

contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")
contract_eth = make_crypto_contract("ETH")


# TODO: Show extrema of multiple contracts
# TODO: Fetch current positions
# TODO: Fetch current orders
# TODO: TA-lib pattern recognition?

# TODO: Remove old S/R if not exists anymore (front)
# TODO: Current countdown at label (front)
# TODO: Special color for double S/R (front)


async def on_px_updated(e: OnPxDataUpdatedEventNoAccount):
    print(
        f"{datetime.now().strftime('%H:%M:%S')}: "
        f"Px Updated for {e.contract.underSymbol} ({e.proc_sec:.3f} s)"
    )
    await fast_api_socket.emit("pxUpdated", to_socket_message_px_data(e.px_data))


async def on_market_data_received(e: OnMarketDataReceivedEvent):
    print(
        f"{datetime.now().strftime('%H:%M:%S')}: "
        f"Market Px Updated for {e.contract.underSymbol}"
    )
    await fast_api_socket.emit("pxUpdatedMarket", to_socket_message_px_data_market(e.contract, e.px))


app.get_px_data_keep_update(
    contract=contract_mnq,
    duration="86400 S",
    bar_size="1 min",
    on_px_data_updated=on_px_updated,
    on_market_data_received=on_market_data_received,
)

app.get_px_data_keep_update(
    contract=contract_mym,
    duration="86400 S",
    bar_size="1 min",
    on_px_data_updated=on_px_updated,
    on_market_data_received=on_market_data_received,
)

if __name__ == "__main__":
    uvicorn.run("main:fast_api", host="127.0.0.1", port=5000)
