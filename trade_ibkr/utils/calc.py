import numpy as np


def closest_diff(num_list: list[float], num: float) -> float:
    num_list = np.asarray(num_list)
    return (np.abs(num_list - num)).min()


def force_min_tick(val: float, tick: float) -> float:
    return val - val % tick


def cdf(val: float, data: list[float]) -> float:
    return sum(abs(val) > abs(item) for item in data) / len(data)
