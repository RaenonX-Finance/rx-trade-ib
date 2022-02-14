from typing import Literal, TypeAlias

OrderSideConst: TypeAlias = Literal["BUY", "SELL"]

OrderTypeConst: TypeAlias = Literal["LMT", "STP"]

ExecutionSideConst: TypeAlias = Literal["BOT", "SLD"]
