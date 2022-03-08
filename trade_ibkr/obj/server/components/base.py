import asyncio
import threading
import time
from abc import ABC

from ibapi.client import EClient
from ibapi.common import TickerId
from ibapi.wrapper import EWrapper

from trade_ibkr.model import OnError, OnErrorEvent
from trade_ibkr.utils import print_log


_error_code_ignore: set[int] = {
    202,  # Order canceled
    2109,  # Out of RTH order is still processed
}


class IBapiBase(EWrapper, EClient, ABC):
    def _connect(self):
        self.connect(
            "localhost",
            8385,  # Configured at TWS
            77
        )

        def run_loop():
            while not self.isConnected():
                print_log("[System] Waiting the app to connect...")
                time.sleep(0.25)

            try:
                self.run()
            except Exception as ex:
                self.disconnect()
                raise ex

        api_thread = threading.Thread(target=run_loop)
        api_thread.start()

    def __init__(self):
        EClient.__init__(self, self)

        # Start from 1 to avoid false-negative
        self._request_id = 1

        self._on_error_handler: OnError | None = None

        self._connect()

    def set_on_error(self, on_error: OnError):
        self._on_error_handler = on_error

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        super().error(reqId, errorCode, errorString)

        if not self._on_error_handler or errorCode in _error_code_ignore:
            return

        async def execute_on_error():
            await self._on_error_handler(OnErrorEvent(
                code=errorCode,
                message=errorString,
            ))

        asyncio.run(execute_on_error())

    @property
    def next_valid_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
