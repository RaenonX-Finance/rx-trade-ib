from dataclasses import dataclass

from .type import ContractType


@dataclass(kw_only=True)
class ContractParams:
    symbol: str
    exchange: str
    type_: ContractType

    def __str__(self):
        return f"{self.symbol} @ {self.exchange} ({self.type_})"
