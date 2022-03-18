from dataclasses import dataclass
from typing import Any, Callable, Coroutine, TypeAlias

from ibapi.contract import Contract, ContractDetails

from trade_ibkr.model import Account, PxData


@dataclass(kw_only=True)
class OnPxDataUpdatedEvent:
    px_data: PxData
    account: Account
    contract: Contract

    is_new_bar: bool


OnPxDataUpdated: TypeAlias = Callable[[OnPxDataUpdatedEvent], None]


@dataclass(kw_only=True)
class OnPxDataUpdatedEventNoAccount:
    contract: ContractDetails
    px_data: PxData

    proc_sec: float

    def __str__(self):
        return (
            f"{self.px_data.contract_symbol} ({self.px_data.contract_identifier}) - "
            f"{self.px_data.current_close:.2f} / {self.px_data.latest_time} "
            f"@ {self.px_data.period_sec // 60} / {self.proc_sec:.3f} s"
        )


OnPxDataUpdatedNoAccount: TypeAlias = Callable[[OnPxDataUpdatedEventNoAccount], Coroutine[Any, Any, None]]


@dataclass(kw_only=True)
class OnMarketDataReceivedEvent:
    contract: ContractDetails
    px: float

    def __str__(self):
        return f"{self.contract.underSymbol} ({self.contract.contract.conId}) - {self.px:.2f}"


OnMarketDataReceived: TypeAlias = Callable[[OnMarketDataReceivedEvent], Coroutine[Any, Any, None]]
