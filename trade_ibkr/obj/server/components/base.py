from abc import ABC

from ibapi.client import EClient
from ibapi.wrapper import EWrapper


class IBapiBase(EWrapper, EClient, ABC):
    def __init__(self):
        EClient.__init__(self, self)

        # Start from 1 to avoid false-negative
        self._request_id = 1

    @property
    def next_valid_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
