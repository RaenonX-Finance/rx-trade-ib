import json
from typing import TypeAlias, TypedDict

from trade_ibkr.const import (
    PNL_WARNING_PX_DIFF_SMA_RATIO, PNL_WARNING_PX_DIFF_VAL, PNL_WARNING_TOTAL_PNL,
    PNL_WARNING_UNREALIZED_PNL, SR_CUSTOM_LEVELS,
)


class PnLWarningConfig(TypedDict):
    pxDiffVal: float
    pxDiffSmaRatio: float
    totalPnL: float
    unrealizedPnL: float


class CustomSrLevel(TypedDict):
    level: float
    strong: bool


CustomSrLevelDict: TypeAlias = dict[int, list[CustomSrLevel]]


class InitData(TypedDict):
    pnlWarningConfig: PnLWarningConfig
    customSrLevelDict: CustomSrLevelDict


def _to_pnl_warning_config() -> PnLWarningConfig:
    return {
        "pxDiffVal": PNL_WARNING_PX_DIFF_VAL,
        "pxDiffSmaRatio": PNL_WARNING_PX_DIFF_SMA_RATIO,
        "totalPnL": PNL_WARNING_TOTAL_PNL,
        "unrealizedPnL": PNL_WARNING_UNREALIZED_PNL,
    }


def _to_custom_sr_level_dict() -> CustomSrLevelDict:
    return {
        contract_id: [
            {
                "level": sr_level["level"],
                "strong": sr_level.get("strong", False),
            }
            for sr_level in sr_levels
        ]
        for contract_id, sr_levels in SR_CUSTOM_LEVELS.items()
    }


def to_socket_message_init_data() -> str:
    data: InitData = {
        "pnlWarningConfig": _to_pnl_warning_config(),
        "customSrLevelDict": _to_custom_sr_level_dict(),
    }

    return json.dumps(data)
