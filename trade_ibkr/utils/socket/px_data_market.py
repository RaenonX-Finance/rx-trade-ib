import json
from typing import TypedDict

from ibapi.contract import ContractDetails

from ..contract import get_unique_identifier


class PxDataMarket(TypedDict):
    contractId: int
    px: float


def to_socket_message_px_data_market(contract: ContractDetails, px: float) -> str:
    data: PxDataMarket = {
        "contractId": get_unique_identifier(contract),
        "px": px,
    }

    return json.dumps(data)
