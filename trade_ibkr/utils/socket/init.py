import json
from typing import TypedDict

from trade_ibkr.const import (
    PNL_WARNING_PX_DIFF_SMA_RATIO, PNL_WARNING_PX_DIFF_VAL, PNL_WARNING_TOTAL_PNL,
    PNL_WARNING_UNREALIZED_PNL,
)


class PnLWarningConfig(TypedDict):
    pxDiffVal: float
    pxDiffSmaRatio: float
    totalPnL: float
    unrealizedPnL: float


class InitData(TypedDict):
    pnlWarningConfig: PnLWarningConfig


def _to_pnl_warning_config() -> PnLWarningConfig:
    return {
        "pxDiffVal": PNL_WARNING_PX_DIFF_VAL,
        "pxDiffSmaRatio": PNL_WARNING_PX_DIFF_SMA_RATIO,
        "totalPnL": PNL_WARNING_TOTAL_PNL,
        "unrealizedPnL": PNL_WARNING_UNREALIZED_PNL,
    }


def to_socket_message_init_data() -> str:
    data: InitData = {
        "pnlWarningConfig": _to_pnl_warning_config(),
    }

    return json.dumps(data)
