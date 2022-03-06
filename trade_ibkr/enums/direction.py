from enum import Enum, auto
from typing import Literal, TypeAlias


DirectionConst: TypeAlias = Literal["UP", "DOWN"]


class Direction(Enum):
    UP = auto()
    DOWN = auto()

    @property
    def const(self) -> DirectionConst:
        if self == Direction.UP:
            return "UP"

        if self == Direction.DOWN:
            return "DOWN"

        raise ValueError(f"Unable to translate {self} to `DirectionConst`")
