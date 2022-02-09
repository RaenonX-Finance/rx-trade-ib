"""
Most of the source code originated from:
https://medium.datadriveninvestor.com/how-to-detect-support-resistance-levels-and-breakout-using-python-f8b5dac42f21.
"""
import numpy as np
from pandas import DataFrame

from trade_ibkr.enums import PxDataCol


def is_far_from_level(value: float, levels: list[float], df: DataFrame) -> bool:
    avg = np.mean(df[PxDataCol.HIGH] - df[PxDataCol.LOW])
    return np.sum([abs(value - level) < avg for level in levels]) == 0


def support_resistance_fractal(df: DataFrame) -> list[float]:
    def is_bullish_fractal(df, i):
        cond1 = df[PxDataCol.LOW][i] < df[PxDataCol.LOW][i - 1]
        cond2 = df[PxDataCol.LOW][i] < df[PxDataCol.LOW][i + 1]
        cond3 = df[PxDataCol.LOW][i + 1] < df[PxDataCol.LOW][i + 2]
        cond4 = df[PxDataCol.LOW][i - 1] < df[PxDataCol.LOW][i - 2]
        return cond1 and cond2 and cond3 and cond4

    def is_bearish_fractal(df, i):
        cond1 = df[PxDataCol.HIGH][i] > df[PxDataCol.HIGH][i - 1]
        cond2 = df[PxDataCol.HIGH][i] > df[PxDataCol.HIGH][i + 1]
        cond3 = df[PxDataCol.HIGH][i + 1] > df[PxDataCol.HIGH][i + 2]
        cond4 = df[PxDataCol.HIGH][i - 1] > df[PxDataCol.HIGH][i - 2]
        return cond1 and cond2 and cond3 and cond4

    levels = []

    for i in range(2, len(df.index) - 2):
        if is_bullish_fractal(df, i):
            low = df[PxDataCol.LOW][i]
            if is_far_from_level(low, levels, df):
                levels.append(low)
        elif is_bearish_fractal(df, i):
            high = df[PxDataCol.HIGH][i]
            if is_far_from_level(high, levels, df):
                levels.append(high)

    return sorted(levels)


def support_resistance_window(df: DataFrame) -> list[float]:
    levels = []
    max_list = []
    min_list = []

    for i in range(5, len(df.index) - 5):
        # taking a window of 9 candles
        high_range = df[PxDataCol.HIGH][i - 5:i + 4]
        current_max = high_range.max()

        # if we find a new maximum value, empty the max_list
        if current_max not in max_list:
            max_list = []

        max_list.append(current_max)

        # if the maximum value remains the same after shifting 5 times
        if len(max_list) == 5 and is_far_from_level(current_max, levels, df):
            levels.append(current_max)

        low_range = df[PxDataCol.LOW][i - 5:i + 5]
        current_min = low_range.min()

        if current_min not in min_list:
            min_list = []

        min_list.append(current_min)

        if len(min_list) == 5 and is_far_from_level(current_min, levels, df):
            levels.append(current_min)

    return sorted(levels)
