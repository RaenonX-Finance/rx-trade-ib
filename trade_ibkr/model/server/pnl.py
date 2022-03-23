from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from ..pnl import PnL


@dataclass(kw_only=True)
class OnPnLUpdatedEvent:
    pnl_dict: dict[int, PnL]

    def __str__(self):
        return " / ".join(f"{contract_id}: {pnl}" for contract_id, pnl in self.pnl_dict.items())


OnPnLUpdated = Callable[[OnPnLUpdatedEvent], Coroutine[Any, Any, None]]
