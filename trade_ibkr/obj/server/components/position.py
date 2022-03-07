import asyncio
from abc import ABC
from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.model import OnPositionFetched, OnPositionFetchedEvent, Position, PositionData
from trade_ibkr.utils import print_error
from .base import IBapiBase


class IBapiPosition(IBapiBase, ABC):
    def __init__(self):
        super().__init__()

        self._position_data_list: list[PositionData] = []
        self._position_on_fetched: OnPositionFetched | None = None

    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        super().position(account, contract, position, avgCost)

        self._position_data_list.append(PositionData(
            contract=contract,
            position=position,
            avg_cost=avgCost,
        ))

    def positionEnd(self):
        super().positionEnd()

        if not self._position_on_fetched:
            print_error(
                "Position fetched, but no corresponding handler is set. "
                "Use `set_on_position_fetched()` for setting it.",
            )
            return

        async def execute_after_position_end():
            await self._position_on_fetched(OnPositionFetchedEvent(position=Position(self._position_data_list)))

        asyncio.run(execute_after_position_end())

        self._position_data_list = []

    def request_positions(self):
        self.reqPositions()

    def set_on_position_fetched(self, on_position_fetched: OnPositionFetched):
        self._position_on_fetched = on_position_fetched
