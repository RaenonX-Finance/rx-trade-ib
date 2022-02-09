"""Check https://interactivebrokers.github.io/tws-api/basic_contracts.html for more details."""
from ibapi.contract import Contract


def make_futures_contract(local_symbol: str, exchange: str):
    contract = Contract()
    contract.secType = "FUT"
    contract.exchange = exchange
    contract.localSymbol = local_symbol

    return contract
