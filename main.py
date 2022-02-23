import os
from datetime import datetime

import uvicorn

from trade_ibkr.const import fast_api, fast_api_socket
from trade_ibkr.model import (
    OnExecutionFetchedEvent, OnMarketDataReceivedEvent, OnOpenOrderFetchedEvent, OnOrderFilledEvent,
    OnPositionFetchedEvent,
    OnPxDataUpdatedEventNoAccount,
)
from trade_ibkr.obj import start_app_info
from trade_ibkr.utils import (
    from_socket_message_order, get_detailed_contract_identifier, make_crypto_contract, make_futures_contract,
    print_log, to_socket_message_execution, to_socket_message_open_order, to_socket_message_order_filled,
    to_socket_message_position,
    to_socket_message_px_data, to_socket_message_px_data_list, to_socket_message_px_data_market,
)

fast_api = fast_api  # Binding for `uvicorn`


async def on_px_updated(e: OnPxDataUpdatedEventNoAccount):
    print_log(f"[TWS] Px Updated / HST ({e})")
    await fast_api_socket.emit("pxUpdated", to_socket_message_px_data(e.px_data))


async def on_market_data_received(e: OnMarketDataReceivedEvent):
    print_log(f"[TWS] Px Updated / MKT ({e})")
    await fast_api_socket.emit("pxUpdatedMarket", to_socket_message_px_data_market(e.contract, e.px))


async def on_position_fetched(e: OnPositionFetchedEvent):
    print_log("[TWS] Fetched positions")
    await fast_api_socket.emit(
        "position",
        to_socket_message_position(e.position)
    )


async def on_open_order_fetched(e: OnOpenOrderFetchedEvent):
    print_log(f"[TWS] Fetched open orders ({e})")
    await fast_api_socket.emit(
        "openOrder",
        to_socket_message_open_order(e.open_order)
    )


async def on_executions_fetched(e: OnExecutionFetchedEvent):
    print_log(f"[TWS] Fetched executions ({e})")
    await fast_api_socket.emit(
        "execution",
        to_socket_message_execution(e.executions)
    )


async def on_order_filled(e: OnOrderFilledEvent):
    print_log(f"[TWS] Order Filled ({e})")
    await fast_api_socket.emit("orderFilled", to_socket_message_order_filled(e))


app, _ = start_app_info(is_demo=True)

contract_mnq = make_futures_contract("MNQH2", "GLOBEX")
contract_mym = make_futures_contract("MYM  MAR 22", "ECBOT")
contract_eth = make_crypto_contract("ETH")

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


def request_earliest_execution_time() -> datetime:
    return min([app.get_px_data(req_id).earliest_time for req_id in px_data_req_ids])


app.set_on_position_fetched(on_position_fetched)
app.set_on_open_order_fetched(on_open_order_fetched)
app.set_on_order_filled(on_order_filled)
app.set_on_executions_fetched(on_executions_fetched, request_earliest_execution_time)


@fast_api_socket.on("pxInit")
async def on_request_px_data(*_):
    print_log("[Socket] Received `pxInit`")

    await fast_api_socket.emit(
        "pxInit",
        to_socket_message_px_data_list([app.get_px_data(req_id) for req_id in px_data_req_ids])
    )


@fast_api_socket.on("position")
async def on_request_position(*_):
    print_log("[Socket] Received `position`")
    app.request_positions()


@fast_api_socket.on("openOrder")
async def on_request_open_orders(*_):
    print_log("[Socket] Received `openOrder`")
    app.request_open_orders()


@fast_api_socket.on("execution")
async def on_request_execution(*_):
    print_log("[Socket] Received `execution`")
    app.request_all_executions()


@fast_api_socket.on("orderPlace")
async def on_request_place_order(_, order_content: str):
    message = from_socket_message_order(order_content)

    px_data = None
    for req_id in px_data_req_ids:
        data = app.get_px_data(req_id)

        if get_detailed_contract_identifier(data.contract) == message.contract_identifier:
            px_data = data
            break

    contract = px_data.contract.contract

    print_log(f"[Socket] Received `orderPlace` ({contract.localSymbol} {message.side} @ {message.px or 'MKT'})")
    app.place_order(
        contract=contract,
        side=message.side,
        quantity=message.quantity,
        order_px=message.px,
        current_px=px_data.current_close,
        order_id=message.order_id,
    )


@fast_api_socket.on("orderCancel")
async def on_request_cancel_order(_, order_id: str):
    print_log("[Socket] Received `orderCancel`")
    app.cancel_order(int(order_id))


# Set current process to the highest priority
os.system(f"wmic process where processid={os.getpid()} CALL setpriority realtime")

if __name__ == "__main__":
    uvicorn.run("main:fast_api", host="127.0.0.1", port=8000)
