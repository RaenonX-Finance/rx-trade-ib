from enum import Enum, auto


class OrderSide(Enum):
    LONG = "BUY"
    SHORT = "SELL"

    @property
    def reverse(self) -> "OrderSide":
        match self:
            case OrderSide.LONG:
                return OrderSide.SHORT
            case OrderSide.SHORT:
                return OrderSide.LONG

        raise ValueError(f"Unhandled reversed order side: {self}")

    @property
    def multiplier(self) -> int:
        match self:
            case OrderSide.LONG:
                return 1
            case OrderSide.SHORT:
                return -1

        raise ValueError(f"Unhandled order side: {self}")


class Side(Enum):
    LONG = auto()
    SHORT = auto()
    NEUTRAL = auto()

    @property
    def order_side(self) -> OrderSide:
        match self:
            case Side.LONG:
                return OrderSide.LONG
            case Side.SHORT:
                return OrderSide.SHORT

        raise ValueError("Neutral does not have an order side")

    @property
    def multiplier(self) -> int:
        match self:
            case Side.LONG:
                return 1
            case Side.SHORT:
                return -1

        return 0
