import asyncio
from abc import ABC

from ibapi.common import TickerId

from trade_ibkr.model import OnError, OnErrorEvent
from .base import IBapiBase

_error_code_ignore: set[int] = {
    202,  # Order canceled
    2109,  # Out of RTH order is still processed
}


class IBapiError(IBapiBase, ABC):
    def __init__(self):
        super().__init__()

        self._on_error_handler: OnError | None = None

    def set_on_error(self, on_error: OnError):
        self._on_error_handler = on_error

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        if not self._on_error_handler or errorCode in _error_code_ignore:
            return

        async def execute_on_error():
            await self._on_error_handler(OnErrorEvent(
                code=errorCode,
                message=errorString,
            ))

        asyncio.run(execute_on_error())
