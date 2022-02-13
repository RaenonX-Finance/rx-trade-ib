import os
from datetime import datetime

import uvicorn

from trade_ibkr.const import fast_api, fast_api_socket
from trade_ibkr.model import OnPxDataUpdatedEventNoAccount, OnMarketDataReceivedEvent, OnPositionFetchedEvent
from trade_ibkr.obj import start_app_info
from trade_ibkr.utils import (
    make_futures_contract, make_crypto_contract,
    to_socket_message_px_data, to_socket_message_px_data_market, to_socket_message_px_data_list,
    to_socket_message_position,
)

fast_api = fast_api  # Binding for `uvicorn`


# TODO: TA-lib pattern recognition?

# TODO: Fetch current orders - Marker @ https://jsfiddle.net/TradingView/nd80cx1a/
# TODO: Send orders - double click (front)
# - Check avg px after order
# - Check PnL after order if filled at strike


async def on_px_updated(e: OnPxDataUpdatedEventNoAccount):
    print(
        f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]}: "
        f"Px Updated for {e.contract.underSymbol} ({e.proc_sec:.3f} s)"
    )
    await fast_api_socket.emit("pxUpdated", to_socket_message_px_data(e.px_data))


async def on_market_data_received(e: OnMarketDataReceivedEvent):
    print(
        f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]}: "
        f"Market Px Updated for {e.contract.underSymbol} ({e.px:.2f})"
    )
    await fast_api_socket.emit("pxUpdatedMarket", to_socket_message_px_data_market(e.contract, e.px))


async def on_position_fetched(e: OnPositionFetchedEvent):
    print(
        f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]}: "
        f"Position data fetched"
    )
    await fast_api_socket.emit(
        "position",
        to_socket_message_position(e.position)
    )


app, _ = start_app_info(is_demo=True)
app.set_on_position_fetched(on_position_fetched)

contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")
contract_eth = make_crypto_contract("ETH")

px_data_req_ids: list[int] = [
    app.get_px_data_keep_update(
        contract=contract_mnq,
        duration="2 D",
        bar_size="1 min",
        on_px_data_updated=on_px_updated,
        on_market_data_received=on_market_data_received,
    ),
    app.get_px_data_keep_update(
        contract=contract_mym,
        duration="2 D",
        bar_size="1 min",
        on_px_data_updated=on_px_updated,
        on_market_data_received=on_market_data_received,
    ),
    # app.get_px_data_keep_update(
    #     contract=contract_eth,
    #     duration="2 D",
    #     bar_size="1 min",
    #     on_px_data_updated=on_px_updated,
    #     on_market_data_received=on_market_data_received,
    # ),
]


@fast_api_socket.on("pxInit")
async def on_request_px_data(*_):
    await fast_api_socket.emit(
        "pxInit",
        to_socket_message_px_data_list([app.get_px_data(req_id) for req_id in px_data_req_ids])
    )


@fast_api_socket.on("position")
async def on_request_position(*_):
    app.refresh_positions()


# Set current process to the highest priority
os.system(f"wmic process where processid={os.getpid()} CALL setpriority realtime")

if __name__ == "__main__":
    uvicorn.run("main:fast_api", host="127.0.0.1", port=8000)
