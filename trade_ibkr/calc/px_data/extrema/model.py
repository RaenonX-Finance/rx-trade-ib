from dataclasses import dataclass, field
from typing import NamedTuple

from trade_ibkr.enums import Direction


class Extrema(NamedTuple):
    idx: int
    extrema: float


class ExtremaInfo(NamedTuple):
    px: float
    ampl_avg: float


@dataclass(kw_only=True)
class ExtremaDataPoint:
    length: float
    diff: float
    diff_ampl_ratio: float
    px: float


@dataclass(kw_only=True)
class ExtremaData:
    points: list[ExtremaDataPoint]

    current_direction: Direction
    current_ampl_avg: float
    current_length: float

    points_pos: list[ExtremaDataPoint] = field(init=False)
    points_neg: list[ExtremaDataPoint] = field(init=False)

    def __post_init__(self):
        self.points_pos = [point for point in self.points if point.diff > 0]
        self.points_neg = [point for point in self.points if point.diff < 0]

    @property
    def points_in_use(self) -> list[ExtremaDataPoint]:
        return self.points_pos if self.current_direction == Direction.UP else self.points_neg

    @property
    def last_extrema(self) -> ExtremaDataPoint:
        return self.points[-1]
