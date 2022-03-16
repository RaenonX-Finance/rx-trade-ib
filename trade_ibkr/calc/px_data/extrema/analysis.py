import math

import numpy as np
from pandas import DataFrame

from trade_ibkr.enums import Direction, PxDataCol
from trade_ibkr.utils import avg
from .model import Extrema, ExtremaData, ExtremaDataPoint, ExtremaInfo


def analyze_extrema(df: DataFrame) -> ExtremaData:
    extrema: list[Extrema] = []
    extrema_info: list[ExtremaInfo] = []
    diff_sma_queue: list[float] = []
    direction_last = None

    series_epoch_sec = df[PxDataCol.EPOCH_SEC]
    series_local_min = df[PxDataCol.LOCAL_MIN]
    series_local_max = df[PxDataCol.LOCAL_MAX]
    series_diff_sma = df[PxDataCol.DIFF_SMA]

    data_zip = zip(range(len(df.index)), series_epoch_sec, series_local_min, series_local_max, series_diff_sma)

    for idx, epoch_sec, local_min, local_max, diff_sma in data_zip:
        if diff_sma:
            diff_sma_queue.append(diff_sma)

        # Only count the extrema if it occurs before 3+ period
        if len(df.index) - idx < 3:
            continue

        if local_min and not math.isnan(local_min):
            if direction_last == Direction.DOWN:
                extrema[-1] = min(Extrema(idx, local_min), extrema[-1], key=lambda item: item.extrema)
                continue

            direction_last = Direction.DOWN
            extrema.append(Extrema(idx, local_min))
            extrema_info.append(ExtremaInfo(epoch_sec, local_min, avg(diff_sma_queue), direction_last.const))
            diff_sma_queue = []
            continue
        elif local_max and not math.isnan(local_max):
            if direction_last == Direction.UP:
                extrema[-1] = max(Extrema(idx, local_max), extrema[-1], key=lambda item: item.extrema)
                continue

            direction_last = Direction.UP
            extrema.append(Extrema(idx, local_max))
            extrema_info.append(ExtremaInfo(epoch_sec, local_max, avg(diff_sma_queue), direction_last.const))
            diff_sma_queue = []
            continue

    diff = np.diff(np.concatenate(([Extrema(0, extrema[0].extrema)], extrema)), axis=0)

    return ExtremaData(
        points=[
            ExtremaDataPoint(
                epoch_sec=info.epoch_sec,
                length=int(extrema_diff[0]),
                diff=extrema_diff[1],
                diff_sma_ratio=abs(extrema_diff[1] / info.diff_sma_avg) if info.diff_sma_avg else 0,
                px=info.px,
                direction=info.direction,
            )
            for extrema_diff, info in zip(diff, extrema_info)
        ],
        current_ampl_ratio=(
            abs(df[PxDataCol.CLOSE][-1] - extrema[-1].extrema) / avg(diff_sma_queue)
            if diff_sma_queue
            else 0
        ),
        current_direction=direction_last,
        current_length=len(df.index) - 1 - extrema[-1].idx if extrema else 0
    )
