import json
from typing import Iterable, TYPE_CHECKING, TypedDict

from trade_ibkr.const import SMA_PERIODS, SR_STRONG_THRESHOLD
from trade_ibkr.enums import DirectionConst, PxDataCol
from trade_ibkr.utils import cdf
from .utils import df_rows_to_list_of_data

if TYPE_CHECKING:
    from trade_ibkr.calc import ExtremaDataPoint
    from trade_ibkr.model import PxData


class PxDataBar(TypedDict):
    epochSec: float
    open: float
    high: float
    low: float
    close: float
    vwap: float
    amplitudeHL: float | None
    amplitudeOC: float | None
    extremaMin: bool | None
    extremaMax: bool | None
    ema120: float | None
    ema120Trend: float | None
    ema120TrendChange: float | None
    diff: float
    diffSma: float | None
    diffSmaTrend: float | None


class PxDataSupportResistance(TypedDict):
    level: float
    strength: float
    strengthCount: float
    strong: bool


class PxDataContract(TypedDict):
    identifier: int
    minTick: float
    symbol: str
    multiplier: float


class PxDataLastDayDiff(TypedDict):
    px: float
    percent: float


class PxDataExtremaPoint(TypedDict):
    epochSec: int
    length: int
    diff: float
    diffSmaRatio: float
    px: float
    direction: DirectionConst


class PxDataExtremaCurrentData(TypedDict):
    val: float
    pct: float


class PxDataExtremaCurrentStats(TypedDict):
    diff: PxDataExtremaCurrentData
    diffSmaRatio: PxDataExtremaCurrentData
    length: PxDataExtremaCurrentData


class PxDataExtrema(TypedDict):
    points: list[PxDataExtremaPoint]
    current: PxDataExtremaCurrentStats


class PxDataDict(TypedDict):
    uniqueIdentifier: str
    periodSec: int
    contract: PxDataContract
    data: list[PxDataBar]
    extrema: PxDataExtrema
    supportResistance: list[PxDataSupportResistance]
    lastDayClose: float | None
    isMajor: bool
    smaPeriods: list[int]


def _from_px_data_bars(px_data: "PxData") -> list[PxDataBar]:
    columns = {
        PxDataCol.EPOCH_SEC: "epochSec",
        PxDataCol.OPEN: "open",
        PxDataCol.HIGH: "high",
        PxDataCol.LOW: "low",
        PxDataCol.CLOSE: "close",
        PxDataCol.VWAP: "vwap",
        PxDataCol.AMPLITUDE_HL_EMA_10: "amplitudeHL",
        PxDataCol.AMPLITUDE_OC_EMA_10: "amplitudeOC",
        PxDataCol.LOCAL_MIN: "extremaMin",
        PxDataCol.LOCAL_MAX: "extremaMax",
        PxDataCol.EMA_120: "ema120",
        PxDataCol.EMA_120_TREND: "ema120Trend",
        PxDataCol.EMA_120_TREND_CHANGE: "ema120TrendChange",
        PxDataCol.DIFF: "diff",
        PxDataCol.DIFF_SMA: "diffSma",
        PxDataCol.DIFF_SMA_TREND: "diffSmaTrend",
    }
    columns |= {
        PxDataCol.get_sma_col_name(sma_period): f"sma{sma_period}"
        for sma_period in SMA_PERIODS
    }

    df = px_data.dataframe.copy()
    df[PxDataCol.LOCAL_MIN] = df[PxDataCol.LOCAL_MIN].astype(bool)
    df[PxDataCol.LOCAL_MAX] = df[PxDataCol.LOCAL_MAX].astype(bool)

    return df_rows_to_list_of_data(px_data.dataframe, columns)


def _from_px_data_support_resistance(px_data: "PxData") -> list[PxDataSupportResistance]:
    ret: list[PxDataSupportResistance] = []

    max_strength = max(px_data.sr_levels_data.levels_data, key=lambda data: data.strength).strength

    for sr_level in px_data.sr_levels_data.levels_data:
        # Convert integral absolute strength (5) to relative strength (5 / 10 = 0.5)
        strength = sr_level.strength / max_strength

        ret.append({
            "level": sr_level.level,
            "strength": strength,
            "strengthCount": sr_level.strength,
            "strong": strength > SR_STRONG_THRESHOLD
        })

    return ret


def _from_px_data_contract(px_data: "PxData") -> PxDataContract:
    return {
        "identifier": px_data.contract_identifier,
        "symbol": px_data.contract_symbol,
        "minTick": px_data.contract.minTick,
        "multiplier": float(px_data.contract.contract.multiplier or 1),
    }


def _from_px_data_current_stats(px_data: "PxData") -> PxDataExtremaCurrentStats:
    points = px_data.extrema.points_in_use

    diff = px_data.current_close - px_data.extrema.last_extrema.px
    ampl_ratio = px_data.extrema.current_ampl_ratio
    length = px_data.extrema.current_length

    return {
        "diff": {
            "val": diff,
            "pct": (1 - cdf(diff, list(map(lambda point: point.diff, points)))) * 100,
        },
        "diffSmaRatio": {
            "val": ampl_ratio,
            "pct": (1 - cdf(ampl_ratio, list(map(lambda point: point.diff_sma_ratio, points)))) * 100,
        },
        "length": {
            "val": length,
            "pct": (1 - cdf(length, list(map(lambda point: point.length, points)))) * 100,
        },
    }


def _from_px_data_extrema_point(point: "ExtremaDataPoint") -> PxDataExtremaPoint:
    return {
        "epochSec": point.epoch_sec,
        "length": point.length,
        "diff": point.diff,
        "diffSmaRatio": point.diff_sma_ratio,
        "px": point.px,
        "direction": point.direction,
    }


def _from_px_data_extrema(px_data: "PxData") -> PxDataExtrema:
    return {
        "points": [_from_px_data_extrema_point(point) for point in px_data.extrema.points],
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
        "lastDayClose": px_data.get_last_day_close(),
        "isMajor": px_data.is_major,
        "smaPeriods": SMA_PERIODS,
    }


def to_socket_message_px_data(px_data: "PxData") -> str:
    return json.dumps(_to_px_data_dict(px_data))


def to_socket_message_px_data_list(px_data_list: Iterable["PxData"]) -> str:
    data: list[PxDataDict] = [_to_px_data_dict(px_data) for px_data in px_data_list if px_data]

    return json.dumps(data)
