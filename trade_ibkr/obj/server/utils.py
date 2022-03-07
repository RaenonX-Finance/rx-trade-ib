import threading
import time

from trade_ibkr.utils import print_log
from .main import IBapiServer


def start_ib_server(*, is_demo: bool = False, client_id: int | None = None) -> tuple[IBapiServer, threading.Thread]:
    app = IBapiServer()
    app.connect(
        "localhost",
        8384 if is_demo else 8383,  # Configured at TWS
        client_id or (50 if is_demo else 100)
    )

    def run_loop():
        try:
            app.run()
        except Exception as ex:
            app.disconnect()
            raise ex

    api_thread = threading.Thread(target=run_loop)
    api_thread.start()

    while not app.isConnected():
        print_log("[System] Waiting the app to connect...")
        time.sleep(0.25)

    return app, api_thread
