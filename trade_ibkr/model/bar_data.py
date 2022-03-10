from datetime import datetime

from ibapi.common import BarData

from trade_ibkr.enums import PxDataCol


BarDataDict = dict[PxDataCol, float | int]


def to_bar_data_dict(data: BarData, *, is_date_ymd: bool) -> BarDataDict:
    epoch_sec = data.date

    if is_date_ymd:
        epoch_sec = int(datetime.strptime(epoch_sec, "%Y%m%d").timestamp())
    else:
        epoch_sec = int(data.date)

    return {
        PxDataCol.OPEN: float(data.open),
        PxDataCol.HIGH: float(data.high),
        PxDataCol.LOW: float(data.low),
        PxDataCol.CLOSE: float(data.close),
        PxDataCol.EPOCH_SEC: epoch_sec,
        PxDataCol.VOLUME: int(data.volume),
    }
