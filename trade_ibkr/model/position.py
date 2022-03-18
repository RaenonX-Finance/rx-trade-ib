from dataclasses import dataclass, field
from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.enums import Side
from trade_ibkr.utils import get_contract_identifier, get_basic_contract_symbol


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
        self._data: dict[int, PositionData] = {
            get_contract_identifier(position.contract): position
            for position in data
        }

    def get_position_data(self, contract_identifier: int) -> PositionData | None:
        return self._data.get(contract_identifier)

    def get_position_side(self, contract_identifier: int) -> Side:
        position_data = self.get_position_data(contract_identifier)

        return position_data.side if position_data else Side.NEUTRAL

    def update_position(self, position_data: PositionData) -> None:
        """
        This should be used by backtest account only.

        For broker account, re-fetch all positions instead.
        """
        self._data[get_contract_identifier(position_data.contract)] = position_data

    def has_position(self, contract_identifier: int) -> bool:
        return contract_identifier in self._data and self._data[contract_identifier].position != Decimal(0)

    @property
    def data(self) -> dict[int, PositionData]:
        return self._data

    def __str__(self):
        position_text = [
            f"{get_basic_contract_symbol(pos.contract)}: {pos.position}"
            for pos in self._data.values() if pos.position != 0
        ]

        # Could have data with 0 position
        if not position_text:
            return "(No position)"

        return " / ".join(position_text)
