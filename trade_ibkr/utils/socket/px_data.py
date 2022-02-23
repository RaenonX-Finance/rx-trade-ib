import json
from typing import TypedDict, TYPE_CHECKING

from trade_ibkr.enums import PxDataCol

if TYPE_CHECKING:
    from trade_ibkr.model import PxData


class PxDataBar(TypedDict):
    epochSec: float
    open: float
    high: float
    low: float
    close: float
    vwap: float
    amplitudeHL: float
    amplitudeOC: float
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


class PxDataDict(TypedDict):
    uniqueIdentifier: str
    periodSec: int
    contract: PxDataContract
    data: list[PxDataBar]
    supportResistance: list[PxDataSupportResistance]


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
            "amplitudeHL": px_data_row[PxDataCol.AMPLITUDE_HL],
            "amplitudeOC": px_data_row[PxDataCol.AMPLITUDE_OC],
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


def _to_px_data_dict(px_data: "PxData") -> PxDataDict:
    return {
        "uniqueIdentifier": px_data.unique_identifier,
        "periodSec": px_data.period_sec,
        "contract": _from_px_data_contract(px_data),
        "data": _from_px_data_bars(px_data),
        "supportResistance": _from_px_data_support_resistance(px_data),
    }


def to_socket_message_px_data(px_data: "PxData") -> str:
    return json.dumps(_to_px_data_dict(px_data))


def to_socket_message_px_data_list(px_data_list: list["PxData"]) -> str:
    data: list[PxDataDict] = [_to_px_data_dict(px_data) for px_data in px_data_list if px_data]

    return json.dumps(data)
