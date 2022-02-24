from dataclasses import dataclass, field
from typing import TypedDict

from pandas import DataFrame


@dataclass(kw_only=True)
class SRLevel:
    level: float
    fractal: bool
    window: bool


class SRLevelInitData(TypedDict):
    fractal: list[float]
    window: list[float]


@dataclass(kw_only=True)
class SRLevelsData:
    levels: SRLevelInitData

    bar_hl_avg: float

    df: DataFrame

    levels_data: dict[float, SRLevel] = field(init=False)

    def _init_get_level_data(self):
        for key, levels in sorted(self.levels.items(), key=lambda item: len(item[1])):
            for current_level in levels:
                is_close_to_level = False

                for level_of_data in self.levels_data.keys():
                    if abs(level_of_data - current_level) > self.bar_hl_avg:
                        continue

                    self.levels_data[level_of_data].window = (
                            self.levels_data[level_of_data].window
                            or key == "window"
                    )
                    self.levels_data[level_of_data].fractal = (
                            self.levels_data[level_of_data].fractal
                            or key == "fractal"
                    )
                    is_close_to_level = True
                    break

                if is_close_to_level:
                    continue

                self.levels_data[current_level] = SRLevel(
                    level=current_level,
                    window=key == "window",
                    fractal=key == "fractal"
                )

    def __post_init__(self):
        self.levels_data = {}

        self._init_get_level_data()
