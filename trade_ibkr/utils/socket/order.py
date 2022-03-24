import json
from dataclasses import dataclass
from typing import TypedDict

from trade_ibkr.enums import OrderSideConst


class OrderSocketMessage(TypedDict):
    orderId: int | None
    identifier: int
    side: OrderSideConst
    quantity: float
    px: float | None
    periodSec: int
    forceBracket: bool | None


@dataclass(kw_only=True)
class OrderSocketMessagePack:
    order_id: int | None
    contract_identifier: int
    side: OrderSideConst
    quantity: float
    px: float | None
    period_sec: int
    force_bracket: bool | None


def from_socket_message_order(message: str) -> OrderSocketMessagePack:
    order_message: OrderSocketMessage = json.loads(message)

    return OrderSocketMessagePack(
        order_id=order_message.get("orderId"),
        contract_identifier=order_message["identifier"],
        side=order_message["side"],
        quantity=order_message["quantity"],
        px=order_message["px"],
        period_sec=order_message["periodSec"],
        force_bracket=order_message["forceBracket"],
    )
