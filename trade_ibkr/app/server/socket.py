from trade_ibkr.const import fast_api_socket
from trade_ibkr.enums import SocketEvent
from trade_ibkr.obj import IBapiServer
from trade_ibkr.utils import (
    from_socket_message_order, print_log,
    to_socket_message_init_data, to_socket_message_px_data_list,
)
from .utils import get_px_data_by_contract_identifier


def register_socket_endpoints(app: IBapiServer, px_data_req_ids: list[int]):
    @fast_api_socket.on(SocketEvent.INIT)
    async def on_request_init_data(*_):
        print_log("[Socket] Received `init`")

        await fast_api_socket.emit(
            SocketEvent.INIT,
            to_socket_message_init_data()
        )

    @fast_api_socket.on(SocketEvent.PX_INIT)
    async def on_request_px_data_init(*_):
        print_log("[Socket] Received `pxInit`")

        await fast_api_socket.emit(
            SocketEvent.PX_INIT,
            to_socket_message_px_data_list(app.get_px_data_from_cache(req_id) for req_id in px_data_req_ids)
        )

    @fast_api_socket.on(SocketEvent.POSITION)
    async def on_request_position(*_):
        print_log("[Socket] Received `position`")
        app.request_positions()

    @fast_api_socket.on(SocketEvent.OPEN_ORDER)
    async def on_request_open_orders(*_):
        print_log("[Socket] Received `openOrder`")
        app.request_open_orders()

    @fast_api_socket.on(SocketEvent.EXECUTION)
    async def on_request_execution(*_):
        print_log("[Socket] Received `execution`")
        app.request_all_executions()

    @fast_api_socket.on(SocketEvent.PLACE_ORDER)
    async def on_request_place_order(_, order_content: str):
        message = from_socket_message_order(order_content)

        px_data = get_px_data_by_contract_identifier(
            app, px_data_req_ids,
            message.contract_identifier, message.period_sec
        )
        contract = px_data.contract.contract

        print_log(f"[Socket] Received `orderPlace` ({contract.localSymbol} {message.side} @ {message.px or 'MKT'})")
        app.place_order(
            contract=contract,
            side=message.side,
            quantity=message.quantity,
            order_px=message.px,
            current_px=px_data.current_close,
            diff_sma=px_data.current_diff_sma,
            order_id=message.order_id,
            min_tick=px_data.contract.minTick,
        )

    @fast_api_socket.on(SocketEvent.CANCEL_ORDER)
    async def on_request_cancel_order(_, order_id: str):
        print_log("[Socket] Received `orderCancel`")
        app.cancel_order(int(order_id))
