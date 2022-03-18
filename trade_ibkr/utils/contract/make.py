"""Check https://interactivebrokers.github.io/tws-api/basic_contracts.html for more details."""
from ibapi.contract import Contract

from .model import ContractParams


def make_futures_contract(params: ContractParams) -> Contract:
    contract = Contract()
    contract.secType = "FUT"
    contract.exchange = params.exchange
    contract.localSymbol = params.symbol

    return contract


def make_crypto_contract(params: ContractParams) -> Contract:
    contract = Contract()
    contract.symbol = params.symbol
    contract.secType = "CRYPTO"
    contract.exchange = "PAXOS"
    contract.currency = "USD"

    return contract


def make_index_contract(params: ContractParams) -> Contract:
    contract = Contract()
    contract.symbol = params.symbol
    contract.secType = "IND"
    contract.exchange = params.exchange
    contract.currency = "USD"

    return contract


def make_contract_from_unique_identifier(identifier: int) -> Contract:
    contract = Contract()
    contract.conId = identifier

    return contract
