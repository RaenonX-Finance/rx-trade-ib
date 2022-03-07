import json
from dataclasses import dataclass
from typing import TypedDict

from ibapi.contract import ContractDetails

from ..contract import get_detailed_contract_identifier


class PxDataMarket(TypedDict):
    contractId: int
    px: float


def to_socket_message_px_data_market(contract: ContractDetails, px: float) -> str:
    data: PxDataMarket = {
        "contractId": get_detailed_contract_identifier(contract),
        "px": px,
    }

    return json.dumps(data)


@dataclass(kw_only=True)
class PxDataMarketPack:
    contract_id: int
    px: float


def from_socket_message_px_data_market(message: str) -> PxDataMarketPack:
    market_px: PxDataMarket = json.loads(message)

    return PxDataMarketPack(
        contract_id=market_px["contractId"],
        px=market_px["px"],
    )
