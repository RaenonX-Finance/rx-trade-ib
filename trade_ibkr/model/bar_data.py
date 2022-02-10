from ibapi.common import BarData

from trade_ibkr.enums import PxDataCol


BarDataDict = dict[PxDataCol, float | int]


def to_bar_data_dict(data: BarData) -> BarDataDict:
    # noinspection PyTypeChecker
    return {
        PxDataCol.OPEN: float(data.open),
        PxDataCol.HIGH: float(data.high),
        PxDataCol.LOW: float(data.low),
        PxDataCol.CLOSE: float(data.close),
        PxDataCol.EPOCH_SEC: int(data.date),
        PxDataCol.VOLUME: int(data.volume),
        PxDataCol.VWAP: float(data.wap),
    }
