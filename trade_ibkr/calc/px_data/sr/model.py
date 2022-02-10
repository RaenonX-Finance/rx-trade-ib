from dataclasses import dataclass, field
from typing import TypedDict


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

    levels_data: dict[float, SRLevel] = field(init=False)

    def __post_init__(self):
        self.levels_data = {}

        for key, levels in self.levels.items():
            for current_level in levels:
                is_close_to_level = False

                for level_of_data, data in self.levels_data.items():
                    if abs(level_of_data - current_level) > self.bar_hl_avg:
                        continue

                    data.window = key == "window"
                    data.fractal = key == "fractal"
                    is_close_to_level = True
                    break

                if is_close_to_level:
                    continue

                self.levels_data[current_level] = SRLevel(
                    level=current_level,
                    window=key == "window",
                    fractal=key == "fractal"
                )
