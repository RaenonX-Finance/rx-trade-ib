from enum import Enum, auto


class OrderSide(Enum):
    LONG = "BUY"
    SHORT = "SELL"

    @property
    def reverse(self) -> "OrderSide":
        if self == OrderSide.LONG:
            return OrderSide.SHORT
        if self == OrderSide.SHORT:
            return OrderSide.LONG

        raise ValueError(f"Unhandled reversed order side: {self}")

    @property
    def multiplier(self) -> int:
        if self == OrderSide.LONG:
            return 1
        if self == OrderSide.SHORT:
            return -1

        raise ValueError(f"Unhandled order side: {self}")


class Side(Enum):
    LONG = auto()
    SHORT = auto()
    NEUTRAL = auto()

    @property
    def order_side(self) -> OrderSide:
        if self == Side.LONG:
            return OrderSide.LONG
        if self == Side.SHORT:
            return OrderSide.SHORT

        raise ValueError("Neutral does not have an order side")

    @property
    def multiplier(self) -> int:
        if self == Side.LONG:
            return 1
        if self == Side.SHORT:
            return -1

        return 0
