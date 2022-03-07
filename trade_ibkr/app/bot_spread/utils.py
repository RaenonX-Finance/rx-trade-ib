import numpy as np
from pandas import Series


def get_spread(on_high: Series, on_low: Series) -> Series:
    # On Low = MYM - On High = MNQ
    # MYM / MNQ gives the correct result
    return np.log(on_low.divide(on_high))
