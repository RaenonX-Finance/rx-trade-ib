from abc import ABC

from .contract import IBapiBaseContract
from .order import IBapiBaseOrder


class IBapiBase(IBapiBaseContract, IBapiBaseOrder, ABC):
    pass
