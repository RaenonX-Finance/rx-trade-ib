import os

import uvicorn

from trade_ibkr.const import fast_api, fast_api_socket
from trade_ibkr.model import (
    OnExecutionFetchedEvent, OnMarketDataReceivedEvent, OnOpenOrderFetchedEvent, OnPositionFetchedEvent,
    OnPxDataUpdatedEventNoAccount,
)
from trade_ibkr.obj import start_app_info
from trade_ibkr.utils import (
    make_crypto_contract, make_futures_contract, print_log,
    to_socket_message_execution, to_socket_message_open_order, to_socket_message_position,
    to_socket_message_px_data, to_socket_message_px_data_list, to_socket_message_px_data_market,
    from_socket_message_order, get_detailed_contract_identifier,
)

fast_api = fast_api  # Binding for `uvicorn`


# TODO: TA-lib pattern recognition?

# TODO: Edit orders (list at the left of the order inputs)
# - Show avg px after placement / Show PnL after order filled
# TODO: Cancel order (list at the left of the order inputs)
# TODO: Calculate Px Data Correlation Coeff
# FIXME: (front) Order entry page show: avg px after placement / PnL after order placement - if available (what if)
# FIXME: (back) refresh exec / open order / current avg px right after placing order
# TODO: (front) allow navigating to the corresponding trade on clicking trade log item


async def on_px_updated(e: OnPxDataUpdatedEventNoAccount):
    print_log(f"Px Updated for {e.contract.underSymbol} ({e.proc_sec:.3f} s)")
    await fast_api_socket.emit("pxUpdated", to_socket_message_px_data(e.px_data))


async def on_market_data_received(e: OnMarketDataReceivedEvent):
    print_log(f"Market Px Updated for {e.contract.underSymbol} ({e.px:.2f})")
    await fast_api_socket.emit("pxUpdatedMarket", to_socket_message_px_data_market(e.contract, e.px))


async def on_position_fetched(e: OnPositionFetchedEvent):
    print_log("Position data fetched")
    await fast_api_socket.emit(
        "position",
        to_socket_message_position(e.position)
    )


async def on_open_order_fetched(e: OnOpenOrderFetchedEvent):
    print_log(f"Open order fetched ({sum(len(orders) for orders in e.open_order.orders.values())})")
    await fast_api_socket.emit(
        "openOrder",
        to_socket_message_open_order(e.open_order)
    )


async def on_executions_fetched(e: OnExecutionFetchedEvent):
    print_log(f"Executions fetched ({sum(len(executions) for executions in e.executions.executions.values())})")
    await fast_api_socket.emit(
        "execution",
        to_socket_message_execution(e.executions)
    )


app, _ = start_app_info(is_demo=True)
app.set_on_position_fetched(on_position_fetched)
app.set_on_open_order_fetched(on_open_order_fetched)
app.set_on_executions_fetched(on_executions_fetched, 60)

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
    print_log("Socket: Received Px Init")

    try:
        await fast_api_socket.emit(
            "pxInit",
            to_socket_message_px_data_list([app.get_px_data(req_id) for req_id in px_data_req_ids])
        )
    except ValueError:
        # PxInit might be called before the PxData initializes
        pass


@fast_api_socket.on("position")
async def on_request_position(*_):
    print_log("Socket: Received Position")
    app.request_positions()


@fast_api_socket.on("openOrder")
async def on_request_open_orders(*_):
    print_log("Socket: Received Open Order")
    app.request_open_orders()


@fast_api_socket.on("execution")
async def on_request_execution(*_):
    print_log("Socket: Received Execution")
    earliest_time = min([app.get_px_data(req_id).earliest_time for req_id in px_data_req_ids])
    app.request_all_executions(earliest_time)


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

    print_log(f"Socket: Received Place Order ({contract.localSymbol} {message.side} @ {message.px or 'MKT'})")
    app.place_order(
        contract=contract,
        side=message.side,
        quantity=message.quantity,
        order_px=message.px,
        current_px=px_data.current_close,
    )


# Set current process to the highest priority
os.system(f"wmic process where processid={os.getpid()} CALL setpriority realtime")

if __name__ == "__main__":
    uvicorn.run("main:fast_api", host="127.0.0.1", port=8000)
