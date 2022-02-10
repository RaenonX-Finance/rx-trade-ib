from dataclasses import dataclass
from typing import Any, Callable, Coroutine, TypeAlias

from ibapi.contract import Contract, ContractDetails

from ...account import Account
from ...px_data import PxData


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


OnPxDataUpdatedNoAccount: TypeAlias = Callable[[OnPxDataUpdatedEventNoAccount], Coroutine[Any, Any, None]]
