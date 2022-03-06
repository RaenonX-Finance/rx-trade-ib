from dataclasses import dataclass
from typing import NamedTuple

from trade_ibkr.enums import Direction, DirectionConst


class Extrema(NamedTuple):
    idx: int
    extrema: float


class ExtremaInfo(NamedTuple):
    epoch_sec: int
    px: float
    ampl_avg: float
    direction: DirectionConst


@dataclass(kw_only=True)
class ExtremaDataPoint:
    epoch_sec: int
    length: int
    diff: float
    diff_ampl_ratio: float
    px: float
    direction: DirectionConst


@dataclass(kw_only=True)
class ExtremaData:
    points: list[ExtremaDataPoint]

    current_direction: Direction
    current_ampl_ratio: float
    current_length: float

    @property
    def points_in_use(self) -> list[ExtremaDataPoint]:
        return (
            [point for point in self.points if point.diff > 0]
            if self.current_direction == Direction.UP else
            [point for point in self.points if point.diff < 0]
        )

    @property
    def last_extrema(self) -> ExtremaDataPoint:
        return self.points[-1]
