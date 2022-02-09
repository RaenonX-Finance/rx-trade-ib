import math
from typing import TYPE_CHECKING

from trade_ibkr.enums import PxDataCol

if TYPE_CHECKING:
    from trade_ibkr.model import PxData


# noinspection PyTypeHints
def has_continuous_2_extrema(
        px_data: "PxData", col_target: "PxDataCol", col_cancel: "PxDataCol", *,
        limit_count: int
) -> bool:
    found_1 = False

    for i in range(1, min(limit_count, len(px_data.dataframe.index))):
        series = px_data.get_last_n(i)

        if not math.isnan(series[col_target]):
            if found_1:
                return True
            else:
                found_1 = True

        if not math.isnan(series[col_cancel]):
            found_1 = False

    return False
