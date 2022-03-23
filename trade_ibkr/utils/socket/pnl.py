import json
from typing import TYPE_CHECKING, TypeAlias, TypedDict

if TYPE_CHECKING:
    from trade_ibkr.model import PnL


class SocketPnL(TypedDict):
    unrealized: float
    realized: float


PnLDict: TypeAlias = dict[int, SocketPnL]


def _from_pnl(pnl: "PnL") -> SocketPnL:
    return {
        "unrealized": pnl.unrealized,
        "realized": pnl.realized,
    }


def to_socket_message_pnl(pnl_dict: dict[int, "PnL"]) -> str:
    data: PnLDict = {
        contract_identifier: _from_pnl(pnl)
        for contract_identifier, pnl in pnl_dict.items()
    }

    return json.dumps(data)
