import time
from dataclasses import dataclass, field
from typing import TypedDict

from pandas import DataFrame

from trade_ibkr.enums import PxDataCol


@dataclass(kw_only=True)
class SRLevel:
    level: float
    fractal: bool
    window: bool

    break_: int = field(init=False)
    hold: int = field(init=False)

    def __post_init__(self):
        self.break_ = 0
        self.hold = 0


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

    def _init_level_data_stats(self):
        levels = sorted(self.levels_data.keys())
        touched_levels: list[float] = []
        touched_level_idx: list[int] = []
        for k_low, k_high, k_date in zip(self.df[PxDataCol.LOW].tolist(), self.df[PxDataCol.HIGH].tolist(),
                                         self.df[PxDataCol.DATE].tolist()):
            if not touched_levels:
                # Find initial level
                for idx, level in enumerate(levels):
                    if k_low < level < k_high:
                        touched_levels.append(level)
                        touched_level_idx.append(idx)
                        break

                continue

            level_lower_idx = max(touched_level_idx[-1] - 1, 0)
            level_lower = levels[level_lower_idx]
            level_higher_idx = min(touched_level_idx[-1] + 1, len(levels) - 1)
            level_higher = levels[level_higher_idx]

            while k_low <= level_lower < k_high:
                touched_levels.append(level_lower)
                touched_level_idx.append(level_lower_idx)

                if level_lower_idx == 0:
                    break

                level_lower_idx = max(level_lower_idx - 1, 0)
                level_lower = levels[level_lower_idx]

            while k_low < level_higher <= k_high:
                touched_levels.append(level_higher)
                touched_level_idx.append(level_higher_idx)

                if level_higher == 0:
                    break

                level_higher_idx = max(level_higher_idx - 1, 0)
                level_higher = levels[level_higher_idx]

        for touched_idx in range(1, len(touched_levels) - 1):
            prev, curr, next_ = touched_levels[touched_idx - 1:touched_idx + 2]

            if prev < curr < next_ or prev > curr > next_:
                self.levels_data[curr].break_ += 1
            elif prev < curr > next_ or prev > curr < next_:
                self.levels_data[curr].hold += 1

    def __post_init__(self):
        self.levels_data = {}

        self._init_get_level_data()
        self._init_level_data_stats()
