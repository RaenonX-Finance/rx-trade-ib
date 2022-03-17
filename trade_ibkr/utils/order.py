from decimal import Decimal

from ibapi.order import Order

from trade_ibkr.enums import OrderSideConst, reverse_order_side
from trade_ibkr.utils import force_min_tick


def make_limit_order(
        side: OrderSideConst, quantity: Decimal, px: float, order_id: int | None = None,
        *, parent_id: int = 0, transmit: bool = True,
) -> Order:
    order = Order()
    if order_id:
        order.orderId = order_id
    order.action = side
    order.totalQuantity = quantity
    order.orderType = "LMT"
    order.outsideRth = True
    order.lmtPrice = px
    order.parentId = parent_id
    order.transmit = transmit

    return order


def make_stop_order(
        side: OrderSideConst, quantity: Decimal, px: float, order_id: int | None = None,
        *, parent_id: int = 0, transmit: bool = True,
) -> Order:
    order = Order()
    if order_id:
        order.orderId = order_id
    order.action = side
    order.totalQuantity = quantity
    order.orderType = "STP"
    order.outsideRth = True
    order.auxPrice = px
    order.parentId = parent_id
    order.transmit = transmit

    return order


def make_stop_limit_order(
        side: OrderSideConst, quantity: Decimal, px: float, order_id: int | None = None,
        *, parent_id: int = 0, transmit: bool = True,
) -> Order:
    order = Order()
    if order_id:
        order.orderId = order_id
    order.action = side
    order.totalQuantity = quantity
    order.orderType = "STP LMT"
    order.outsideRth = True
    order.auxPrice = px
    order.lmtPrice = px
    order.parentId = parent_id
    order.transmit = transmit

    return order


def make_market_order(side: OrderSideConst, quantity: Decimal, order_id: int | None = None) -> Order:
    order = Order()
    if order_id:
        order.orderId = order_id
    order.action = side
    order.totalQuantity = quantity
    order.orderType = "MKT"

    return order


def get_order_trigger_price(order: Order) -> float:
    if order.orderType in ("STP", "STP LMT"):
        return order.auxPrice

    if order.orderType == "LMT":
        return order.lmtPrice

    return order.triggerPrice


def update_order_price(order: Order, px: float):
    if order.orderType == "STP":
        order.auxPrice = px
        return

    if order.orderType == "LMT":
        order.lmtPrice = px
        return

    if order.orderType == "STP LMT":
        order.lmtPrice = px
        order.auxPrice = px
        return

    raise ValueError(f"Order of type {order.orderType} not updated - no corresponding handling implementation")


def make_limit_bracket_order(
        side: OrderSideConst, quantity: Decimal, px: float, order_id: int,
        *, take_profit_px_diff: float, stop_loss_px_diff: float, min_tick: float,
) -> list[Order]:
    diff_coeff = 1 if side == "BUY" else -1
    side_reversed = reverse_order_side(side)

    main_order = make_limit_order(side, quantity, px, order_id, transmit=False)
    take_profit = make_limit_order(
        side_reversed, quantity, force_min_tick(px + take_profit_px_diff * diff_coeff, min_tick), order_id + 1,
        parent_id=order_id, transmit=False,
    )
    stop_loss = make_stop_order(
        side_reversed, quantity, force_min_tick(px - stop_loss_px_diff * diff_coeff, min_tick), order_id + 2,
        parent_id=order_id, transmit=True,
    )

    return [main_order, take_profit, stop_loss]
