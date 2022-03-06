import math

import numpy as np
from pandas import DataFrame

from trade_ibkr.enums import Direction, PxDataCol
from trade_ibkr.utils import avg
from .model import Extrema, ExtremaData, ExtremaDataPoint, ExtremaInfo


def analyze_extrema(df: DataFrame) -> ExtremaData:
    extrema: list[Extrema] = []
    extrema_info: list[ExtremaInfo] = []
    amplitude_queue: list[float] = []
    direction_last = None

    series_local_min = df[PxDataCol.LOCAL_MIN]
    series_local_max = df[PxDataCol.LOCAL_MAX]
    series_ampl_hl = df[PxDataCol.AMPLITUDE_HL]

    data_zip = zip(range(len(df.index)), series_local_min, series_local_max, series_ampl_hl)

    for idx, local_min, local_max, amplitude_hl in data_zip:
        if amplitude_hl:
            amplitude_queue.append(amplitude_hl)

        if local_min and not math.isnan(local_min):
            if direction_last == Direction.DOWN:
                extrema[-1] = min(Extrema(idx, local_min), extrema[-1], key=lambda item: item.extrema)
                continue

            ampl_avg = avg(amplitude_queue) if amplitude_queue else None
            amplitude_queue = []
            extrema.append(Extrema(idx, local_min))
            extrema_info.append(ExtremaInfo(local_min, ampl_avg))
            direction_last = Direction.DOWN
            continue
        elif local_max and not math.isnan(local_max):
            if direction_last == Direction.UP:
                extrema[-1] = max(Extrema(idx, local_max), extrema[-1], key=lambda item: item.extrema)
                continue

            ampl_avg = avg(amplitude_queue) if amplitude_queue else None
            amplitude_queue = []
            extrema.append(Extrema(idx, local_max))
            extrema_info.append(ExtremaInfo(local_max, ampl_avg))
            direction_last = Direction.UP
            continue

    diff = np.diff(np.concatenate(([Extrema(0, extrema[0].extrema)], extrema)), axis=0)

    return ExtremaData(
        points=[
            ExtremaDataPoint(
                length=extrema_diff[0],
                diff=extrema_diff[1],
                diff_ampl_ratio=abs(extrema_diff[1] / info.ampl_avg) if info.ampl_avg else 0,
                px=info.px,
            )
            for extrema_diff, info in zip(diff, extrema_info)
        ],
        current_ampl_avg=(
            abs(df[PxDataCol.CLOSE][-1] - extrema[-1].extrema) / avg(amplitude_queue)
            if amplitude_queue
            else 0
        ),
        current_direction=direction_last,
        current_length=len(df.index) - 1 - extrema[-1].idx if extrema else 0
    )
