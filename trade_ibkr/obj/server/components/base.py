import threading
import time
from abc import ABC

from ibapi.client import EClient
from ibapi.common import TickerId
from ibapi.wrapper import EWrapper

from trade_ibkr.model import OnError, OnErrorEvent
from trade_ibkr.utils import asyncio_run, print_error, print_log

_error_code_ignore: set[int] = {
    202,  # Order canceled
    1102,  # Connection restored
    2104,  # Market data farm connected
    2106,  # Historical market data farm connected
    2109,  # Out of RTH order is still processed
    2150,  # Invalid position trade derived value
    2158,  # Security definition server connection OK
}


class IBapiBase(EWrapper, EClient, ABC):
    def __init__(self):
        EClient.__init__(self, self)

        # Start from 1 to avoid false-negative
        self._request_id = 1

        self._on_error_handler: OnError | None = None

    def activate(self, port: int, client_id: int):
        self.connect(
            "localhost",
            port,  # Configured at TWS
            client_id
        )

        def run_loop():
            while not self.isConnected():
                print_log("[System] Waiting for the app to connect...")
                time.sleep(0.25)

            try:
                self.run()
            except Exception as ex:
                self.disconnect()
                raise ex

        api_thread = threading.Thread(target=run_loop)
        api_thread.start()

    def set_on_error(self, on_error: OnError):
        self._on_error_handler = on_error

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        if errorCode in _error_code_ignore:
            return

        event = OnErrorEvent(code=errorCode, message=errorString)
        print_error(f"[TWS] Error ({event})")

        if not self._on_error_handler:
            return

        async def execute_on_error():
            await self._on_error_handler(event)

        asyncio_run(execute_on_error())

    @property
    def next_valid_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
