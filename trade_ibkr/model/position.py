from dataclasses import dataclass, field
from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.enums import Side


@dataclass(kw_only=True)
class PositionData:
    contract: Contract
    position: Decimal
    avg_cost: float

    avg_px: Decimal = field(init=False)

    def __post_init__(self):
        if self.position:
            self.avg_px = Decimal(self.avg_cost) / Decimal(self.contract.multiplier or 1)
        else:
            self.avg_px = Decimal(0)

    def px_diff(self, px: float) -> Decimal:
        if not self.position:
            return Decimal(0)

        return Decimal(px) - self.avg_px

    @property
    def side(self) -> Side:
        if self.position > 0:
            return Side.LONG
        elif self.position < 0:
            return Side.SHORT

        return Side.NEUTRAL

    @property
    def total_cost(self) -> Decimal:
        """This is negative if the current position is negative (shorting)."""
        return self.position * Decimal(self.avg_cost)


class Position:
    def __init__(self, data: list[PositionData]):
        self._data: dict[str, PositionData] = {
            self._get_contract_unique_identifier(position.contract): position
            for position in data
        }

    @staticmethod
    def _get_contract_unique_identifier(contract: Contract) -> str:
        """The return will be used for indexing the positions."""
        return contract.localSymbol

    def get_position_data(self, contract: Contract) -> PositionData | None:
        return self._data.get(self._get_contract_unique_identifier(contract))

    def get_position_side(self, contract: Contract) -> Side:
        position_data = self.get_position_data(contract)

        return position_data.side if position_data else Side.NEUTRAL

    def update_position(self, position_data: PositionData) -> None:
        """
        This should be used by backtest account only.

        For broker account, re-fetch all positions instead.
        """
        self._data[self._get_contract_unique_identifier(position_data.contract)] = position_data
