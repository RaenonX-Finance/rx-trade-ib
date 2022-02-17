import json
from typing import TYPE_CHECKING, TypedDict

from trade_ibkr.enums import OrderSideConst

if TYPE_CHECKING:
    from trade_ibkr.model import OnOrderFilledEvent


class OrderFilledResult(TypedDict):
    identifier: int
    symbol: str
    action: OrderSideConst
    quantity: float
    fillPx: float


def to_socket_message_order_filled(order_filled_event: "OnOrderFilledEvent") -> str:
    data: OrderFilledResult = {
        "identifier": order_filled_event.identifier,
        "symbol": order_filled_event.symbol,
        "action": order_filled_event.action,
        "quantity": float(order_filled_event.quantity),
        "fillPx": order_filled_event.fill_px,
    }

    return json.dumps(data)
