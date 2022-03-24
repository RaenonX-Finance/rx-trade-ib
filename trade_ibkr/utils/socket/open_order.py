import json
from typing import TYPE_CHECKING, TypeAlias, TypedDict

from trade_ibkr.enums import OrderSideConst
from ..contract import get_contract_identifier

if TYPE_CHECKING:
    from trade_ibkr.model import OpenOrder, OpenOrderBook


class OpenOrderData(TypedDict):
    groupId: int | None
    orderId: int
    identifier: int
    side: OrderSideConst
    quantity: float
    px: float
    type: str


OpenOrderDict: TypeAlias = dict[int, dict[int, OpenOrderData]]


def _from_open_order(open_order: "OpenOrder", *, override_group_id: int | None) -> OpenOrderData:
    group_id = None
    if open_order.has_parent:
        group_id = open_order.parent_id
    elif override_group_id:
        group_id = override_group_id

    return {
        "groupId": group_id,
        "orderId": open_order.order_id,
        "identifier": get_contract_identifier(open_order.contract),
        "side": open_order.side,
        "quantity": float(open_order.quantity),
        "px": open_order.price,
        "type": open_order.type_,
    }


def _from_open_orders(open_orders: list["OpenOrder"]) -> dict[int, OpenOrderData]:
    # Assumes single-level nesting
    parent_ids = {order.parent_id for order in open_orders if order.has_parent}

    return {
        open_order.order_id: _from_open_order(
            open_order,
            override_group_id=open_order.order_id if open_order.order_id in parent_ids else None
        )
        for open_order in open_orders
    }


def to_socket_message_open_order(open_order: "OpenOrderBook") -> str:
    data: OpenOrderDict = {
        identifier: _from_open_orders(open_orders)
        for identifier, open_orders in open_order.orders.items()
    }

    return json.dumps(data)
