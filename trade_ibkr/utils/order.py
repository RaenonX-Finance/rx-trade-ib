from decimal import Decimal

from ibapi.order import Order

from trade_ibkr.enums import OrderSide


def make_limit_order(side: OrderSide, quantity: Decimal, px: float) -> Order:
    order = Order()
    order.action = side.value
    order.totalQuantity = quantity
    order.orderType = "LMT"
    order.lmtPrice = px

    return order


def make_market_order(side: OrderSide, quantity: Decimal) -> Order:
    order = Order()
    order.action = side.value
    order.totalQuantity = quantity
    order.orderType = "MKT"

    return order
