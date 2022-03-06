from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.enums import FetchStatus
from trade_ibkr.model import Position, PositionData
from .common import IBapiBaseCommon


class IBapiBasePosition(IBapiBaseCommon):
    def __init__(self):
        super().__init__()

        self._position_data_list: list[PositionData] = []
        self._position_data: Position | None = None
        self._position_data_fetch_status: FetchStatus = FetchStatus.NOT_FETCHED

    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        super().position(account, contract, position, avgCost)

        self._position_data_fetch_status = FetchStatus.FETCHING
        self._position_data_list.append(PositionData(
            contract=contract,
            position=position,
            avg_cost=avgCost,
        ))

    def positionEnd(self):
        super().positionEnd()

        self._position_data_fetch_status = FetchStatus.COMPLETED
        self._position_data = Position(self._position_data_list)
        self._position_data_list = []

    def request_positions(self):
        if self._position_data_fetch_status != FetchStatus.FETCHING:
            self.reqPositions()
            self._position_data_fetch_status = FetchStatus.FETCHING
