"""Check https://interactivebrokers.github.io/tws-api/basic_contracts.html for more details."""
from ibapi.contract import Contract, ContractDetails


def make_futures_contract(local_symbol: str, exchange: str) -> Contract:
    contract = Contract()
    contract.secType = "FUT"
    contract.exchange = exchange
    contract.localSymbol = local_symbol

    return contract


def make_crypto_contract(symbol: str) -> Contract:
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "CRYPTO"
    contract.exchange = "PAXOS"
    contract.currency = "USD"

    return contract


def get_unique_identifier(contract: ContractDetails) -> int:
    return contract.underConId
