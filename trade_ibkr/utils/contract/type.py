from typing import Callable, Literal, TypeAlias, TYPE_CHECKING

from ibapi.contract import Contract

if TYPE_CHECKING:
    from .model import ContractParams


ContractType: TypeAlias = Literal["Futures", "Index", "Crypto"]

ContractMakerFunction: TypeAlias = Callable[["ContractParams"], Contract]
