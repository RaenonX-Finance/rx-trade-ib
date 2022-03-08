from trade_ibkr.const import fast_api_socket
from trade_ibkr.model import (
    OnErrorEvent, OnExecutionFetchedEvent, OnMarketDataReceivedEvent, OnOpenOrderFetchedEvent, OnOrderFilledEvent,
    OnPositionFetchedEvent, OnPxDataUpdatedEventNoAccount,
)
from trade_ibkr.obj import IBapiServer
from trade_ibkr.utils import (
    print_error, print_log,
    to_socket_message_error, to_socket_message_execution, to_socket_message_open_order, to_socket_message_order_filled,
    to_socket_message_position, to_socket_message_px_data, to_socket_message_px_data_market,
)
from .utils import get_execution_on_fetched_params
from ...enums import SocketEvent


async def on_px_updated(e: OnPxDataUpdatedEventNoAccount):
    print_log(f"[TWS] Px Updated / HST ({e})")
    await fast_api_socket.emit(
        SocketEvent.PX_UPDATED,
        to_socket_message_px_data(e.px_data)
    )


async def on_market_data_received(e: OnMarketDataReceivedEvent):
    print_log(f"[TWS] Px Updated / MKT ({e})")
    await fast_api_socket.emit(
        SocketEvent.PX_UPDATED_MARKET,
        to_socket_message_px_data_market(e.contract, e.px)
    )


async def on_position_fetched(e: OnPositionFetchedEvent):
    print_log(f"[TWS] Fetched positions ({e})")
    await fast_api_socket.emit(
        SocketEvent.POSITION,
        to_socket_message_position(e.position)
    )


async def on_open_order_fetched(e: OnOpenOrderFetchedEvent):
    print_log(f"[TWS] Fetched open orders ({e})")
    await fast_api_socket.emit(
        SocketEvent.OPEN_ORDER,
        to_socket_message_open_order(e.open_order)
    )


async def on_executions_fetched(e: OnExecutionFetchedEvent):
    print_log(f"[TWS] Fetched executions ({e})")
    await fast_api_socket.emit(
        SocketEvent.EXECUTION,
        to_socket_message_execution(e.executions)
    )


async def on_order_filled(e: OnOrderFilledEvent):
    print_log(f"[TWS] Order Filled ({e})")
    await fast_api_socket.emit(
        SocketEvent.ORDER_FILLED,
        to_socket_message_order_filled(e)
    )


async def on_error(e: OnErrorEvent):
    await fast_api_socket.emit(SocketEvent.ERROR, to_socket_message_error(e))


def register_handlers(app: IBapiServer, px_data_req_ids: list[int]):
    app.set_on_position_fetched(on_position_fetched)
    app.set_on_open_order_fetched(on_open_order_fetched)
    app.set_on_order_filled(on_order_filled)
    app.set_on_executions_fetched(on_executions_fetched, get_execution_on_fetched_params(app, px_data_req_ids))
    app.set_on_error(on_error)
