import numpy as np


def closest_diff(num_list: list[float], num: float):
    num_list = np.asarray(num_list)
    return (np.abs(num_list - num)).min()
