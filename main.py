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
)

fast_api = fast_api  # Binding for `uvicorn`


# TODO: TA-lib pattern recognition?

# TODO: Send orders - double click (front)
# - Check avg px after order
# - Check PnL after order if filled at strike
# FIXME: (front) open order polling not working (to be removed after order execution sys completed)
# FIXME: (front) Show current PnL on px line label
# TODO: Show unrealized / realized PNL for each security
# TODO: Update positions and open orders actively upon order filled
# TODO: Calculate Px Data Correlation Coeff


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


# Set current process to the highest priority
os.system(f"wmic process where processid={os.getpid()} CALL setpriority realtime")

if __name__ == "__main__":
    uvicorn.run("main:fast_api", host="127.0.0.1", port=8000)
