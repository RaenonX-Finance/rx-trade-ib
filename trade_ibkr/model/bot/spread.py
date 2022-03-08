from dataclasses import dataclass
from typing import Any, Callable, Coroutine, TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from trade_ibkr.model import Account, CommodityPair, PxDataPair, UnrealizedPnL


@dataclass(kw_only=True)
class OnBotSpreadPxUpdatedEvent:
    account: "Account"
    commodity_pair: "CommodityPair"
    px_data_pair: "PxDataPair"
    unrlzd_pnl: "UnrealizedPnL"
    has_pending_order: bool

    proc_sec: float

    def __str__(self):
        return f"{self.commodity_pair} - {self.unrlzd_pnl.current} - {self.proc_sec:.3f} s"


OnBotSpreadPxUpdated: TypeAlias = Callable[[OnBotSpreadPxUpdatedEvent], Coroutine[Any, Any, None]]
