import socketio

from trade_ibkr.const import MARKET_SOCKET_PATH
from trade_ibkr.obj import ClientBotSpread
from trade_ibkr.utils import from_socket_message_px_data_market, print_log


def attach_socket(app: ClientBotSpread):
    sio_client = socketio.AsyncClient()

    @sio_client.on("pxUpdatedMarket")
    def on_market_updated_from_socket(message: str):
        data = from_socket_message_px_data_market(message)
        app.trigger_market_px_updated(data.contract_id, data.px)

        print_log(f"[Socket] Market Px Updated ({data.contract_id} @ {data.px})")

    print_log(f"[Socket] Socket connecting to {MARKET_SOCKET_PATH}...")
    sio_client.connect(MARKET_SOCKET_PATH, socketio_path="ws/socket.io")
    print_log(f"[Socket] Socket connected to {MARKET_SOCKET_PATH}")
