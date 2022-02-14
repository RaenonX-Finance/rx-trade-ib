import json
from typing import TYPE_CHECKING, TypeAlias, TypedDict

from ..contract import get_contract_identifier

if TYPE_CHECKING:
    from trade_ibkr.model import Position, PositionData


class PositionEntry(TypedDict):
    identifier: int
    position: float
    avgPx: float


PositionDict: TypeAlias = dict[int, PositionEntry]


def _from_position_data(position_data: "PositionData") -> PositionEntry:
    return {
        "identifier": get_contract_identifier(position_data.contract),
        "position": float(position_data.position),
        "avgPx": float(position_data.avg_px),
    }


def to_socket_message_position(position: "Position") -> str:
    data: PositionDict = {
        identifier: _from_position_data(position_data)
        for identifier, position_data in position.data.items()
    }

    return json.dumps(data)
