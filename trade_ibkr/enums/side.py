from enum import Enum, auto

from .ibkr_const import OrderSideConst


class Side(Enum):
    LONG = auto()
    SHORT = auto()
    NEUTRAL = auto()

    @property
    def order_side(self) -> OrderSideConst:
        match self:
            case Side.LONG:
                return "BUY"
            case Side.SHORT:
                return "SELL"

        raise ValueError("Neutral does not have an order side")

    @property
    def multiplier(self) -> int:
        match self:
            case Side.LONG:
                return 1
            case Side.SHORT:
                return -1

        return 0
