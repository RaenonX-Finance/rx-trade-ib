import json
from typing import Iterable, TYPE_CHECKING, TypedDict

from trade_ibkr.enums import PxDataCol
from trade_ibkr.utils import cdf

if TYPE_CHECKING:
    from trade_ibkr.model import PxData


class PxDataBarExtrema(TypedDict):
    min: bool
    max: bool


class PxDataBar(TypedDict):
    epochSec: float
    open: float
    high: float
    low: float
    close: float
    vwap: float
    amplitudeHL: float
    amplitudeOC: float
    extrema: PxDataBarExtrema
    ema120: float


class PxDataSupportResistanceType(TypedDict):
    window: bool
    fractal: bool


class PxDataSupportResistance(TypedDict):
    level: float
    type: PxDataSupportResistanceType


class PxDataContract(TypedDict):
    identifier: int
    minTick: float
    symbol: str
    multiplier: float


class PxDataLastDayDiff(TypedDict):
    px: float
    percent: float


class PxDataExtremaData(TypedDict):
    pos: list[float]
    neg: list[float]


class PxDataExtremaCurrentData(TypedDict):
    val: float
    pct: float


class PxDataExtremaCurrentStats(TypedDict):
    swing: PxDataExtremaCurrentData
    swingAmplRatio: PxDataExtremaCurrentData
    duration: PxDataExtremaCurrentData


class PxDataExtrema(TypedDict):
    swing: PxDataExtremaData
    swingAmplRatio: PxDataExtremaData
    duration: PxDataExtremaData
    current: PxDataExtremaCurrentStats


class PxDataDict(TypedDict):
    uniqueIdentifier: str
    periodSec: int
    contract: PxDataContract
    data: list[PxDataBar]
    extrema: PxDataExtrema
    supportResistance: list[PxDataSupportResistance]
    lastDayClose: float | None


def _from_px_data_bars(px_data: "PxData") -> list[PxDataBar]:
    ret = []

    for _, px_data_row in px_data.dataframe.iterrows():
        ret.append({
            "epochSec": px_data_row[PxDataCol.EPOCH_SEC],
            "open": px_data_row[PxDataCol.OPEN],
            "high": px_data_row[PxDataCol.HIGH],
            "low": px_data_row[PxDataCol.LOW],
            "close": px_data_row[PxDataCol.CLOSE],
            "vwap": px_data_row[PxDataCol.VWAP],
            "amplitudeHL": px_data_row[PxDataCol.AMPLITUDE_HL_EMA_10],
            "amplitudeOC": px_data_row[PxDataCol.AMPLITUDE_OC_EMA_10],
            "extrema": {
                "min": bool(px_data_row[PxDataCol.LOCAL_MIN]),
                "max": bool(px_data_row[PxDataCol.LOCAL_MAX])
            },
            "ema120": px_data_row[PxDataCol.EMA_120],
        })

    return ret


def _from_px_data_support_resistance(px_data: "PxData") -> list[PxDataSupportResistance]:
    ret: list[PxDataSupportResistance] = []

    for level_data in px_data.sr_levels_data.levels_data.values():
        ret.append({
            "level": level_data.level,
            "type": {
                "window": level_data.window,
                "fractal": level_data.fractal,
            },
        })

    return ret


def _from_px_data_contract(px_data: "PxData") -> PxDataContract:
    return {
        "identifier": px_data.contract_identifier,
        "symbol": px_data.contract.underSymbol,
        "minTick": px_data.contract.minTick,
        "multiplier": float(px_data.contract.contract.multiplier or 1),
    }


def _from_px_data_current_stats(px_data: "PxData") -> PxDataExtremaCurrentStats:
    points = px_data.extrema.points_in_use

    swing_diff = px_data.current_close - px_data.extrema.last_extrema.px
    swing_diff_ampl_ratio = px_data.extrema.current_ampl_avg
    duration = px_data.extrema.current_length

    return {
        "swing": {
            "val": swing_diff,
            "pct": (1 - cdf(swing_diff, list(map(lambda point: point.diff, points)))) * 100,
        },
        "swingAmplRatio": {
            "val": swing_diff_ampl_ratio,
            "pct": (1 - cdf(swing_diff_ampl_ratio, list(map(lambda point: point.diff_ampl_ratio, points)))) * 100,
        },
        "duration": {
            "val": duration,
            "pct": (1 - cdf(duration, list(map(lambda point: point.length, points)))) * 100,
        },
    }


def _from_px_data_extrema(px_data: "PxData") -> PxDataExtrema:
    return {
        "swing": {
            "pos": list(map(lambda point: point.diff, px_data.extrema.points_pos)),
            "neg": list(map(lambda point: point.diff, px_data.extrema.points_neg)),
        },
        "swingAmplRatio": {
            "pos": list(map(lambda point: point.diff_ampl_ratio, px_data.extrema.points_pos)),
            "neg": list(map(lambda point: point.diff_ampl_ratio, px_data.extrema.points_neg)),
        },
        "duration": {
            "pos": list(map(lambda point: point.length, px_data.extrema.points_pos)),
            "neg": list(map(lambda point: point.length, px_data.extrema.points_neg)),
        },
        "current": _from_px_data_current_stats(px_data)
    }


def _to_px_data_dict(px_data: "PxData") -> PxDataDict:
    return {
        "uniqueIdentifier": px_data.unique_identifier,
        "periodSec": px_data.period_sec,
        "contract": _from_px_data_contract(px_data),
        "data": _from_px_data_bars(px_data),
        "extrema": _from_px_data_extrema(px_data),
        "supportResistance": _from_px_data_support_resistance(px_data),
        "lastDayClose": px_data.get_last_day_close()
    }


def to_socket_message_px_data(px_data: "PxData") -> str:
    return json.dumps(_to_px_data_dict(px_data))


def to_socket_message_px_data_list(px_data_list: Iterable["PxData"]) -> str:
    data: list[PxDataDict] = [_to_px_data_dict(px_data) for px_data in px_data_list if px_data]

    return json.dumps(data)
