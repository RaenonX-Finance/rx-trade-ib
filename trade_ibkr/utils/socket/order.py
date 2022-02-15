import json
from dataclasses import dataclass
from typing import TypedDict

from trade_ibkr.enums import OrderSideConst


class OrderSocketMessage(TypedDict):
    identifier: int
    side: OrderSideConst
    quantity: float
    px: float | None


@dataclass(kw_only=True)
class OrderSocketMessagePack:
    contract_identifier: int
    side: OrderSideConst
    quantity: float
    px: float | None


def from_socket_message_order(message: str) -> OrderSocketMessagePack:
    order_message: OrderSocketMessage = json.loads(message)

    print(order_message["identifier"])

    return OrderSocketMessagePack(
        contract_identifier=order_message["identifier"],
        side=order_message["side"],
        quantity=order_message["quantity"],
        px=order_message["px"],
    )
