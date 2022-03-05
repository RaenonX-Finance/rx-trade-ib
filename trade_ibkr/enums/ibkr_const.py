from typing import Literal, TypeAlias

OrderSideConst: TypeAlias = Literal["BUY", "SELL"]

ExecutionSideConst: TypeAlias = Literal["BOT", "SLD"]


def reverse_order_side(side: OrderSideConst) -> OrderSideConst:
    if side == "BUY":
        return "SELL"

    if side == "SELL":
        return "BUY"

    raise ValueError(f"Irreversible/unhandled order side: {side}")
