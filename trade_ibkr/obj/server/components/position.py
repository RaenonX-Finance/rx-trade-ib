import asyncio
from abc import ABC
from decimal import Decimal
from typing import Literal

from ibapi.contract import Contract

from trade_ibkr.model import OnPositionFetched, OnPositionFetchedEvent, Position, PositionData
from trade_ibkr.utils import print_error
from .base import IBapiBase


class IBapiPosition(IBapiBase, ABC):
    def __init__(self):
        super().__init__()

        self._position_data_list: list[PositionData] = []
        self._position_data: Position | None = None
        self._position_on_fetched: OnPositionFetched | None | Literal["UNDEFINED"] = "UNDEFINED"

    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        self._position_data_list.append(PositionData(
            contract=contract,
            position=position,
            avg_cost=avgCost,
        ))

    def positionEnd(self):
        if self._position_on_fetched == "UNDEFINED":
            print_error(
                "Position fetched, but no corresponding handler is set. "
                "Use `set_on_position_fetched()` for setting it.\n"
                "If this is intended, use `set_on_position_fetched(None)`",
            )
            return

        self._position_data = Position(self._position_data_list)
        self._position_data_list = []

        if not self._position_on_fetched:
            return

        async def execute_after_position_end():
            # noinspection PyCallingNonCallable
            await self._position_on_fetched(OnPositionFetchedEvent(position=self._position_data))

        asyncio.run(execute_after_position_end())

    def request_positions(self):
        self._position_data_list = []
        self.reqPositions()

    def set_on_position_fetched(self, on_position_fetched: OnPositionFetched | None):
        self._position_on_fetched = on_position_fetched
