from decimal import Decimal

from ibapi.order import Order

from trade_ibkr.enums import OrderSideConst


def make_limit_order(side: OrderSideConst, quantity: Decimal, px: float) -> Order:
    order = Order()
    order.action = side
    order.totalQuantity = quantity
    order.orderType = "LMT"
    order.outsideRth = True
    order.lmtPrice = px

    return order


def make_stop_order(side: OrderSideConst, quantity: Decimal, px: float) -> Order:
    order = Order()
    order.action = side
    order.totalQuantity = quantity
    order.orderType = "STP"
    order.outsideRth = True
    order.auxPrice = px

    return order


def make_market_order(side: OrderSideConst, quantity: Decimal) -> Order:
    order = Order()
    order.action = side
    order.totalQuantity = quantity
    order.orderType = "MKT"

    return order


def get_order_trigger_price(order: Order) -> float:
    if order.orderType == "STP":
        return order.auxPrice

    if order.orderType == "LMT":
        return order.lmtPrice

    return order.triggerPrice
