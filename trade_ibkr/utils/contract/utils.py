from ibapi.contract import Contract, ContractDetails

from ..log import print_error


def get_basic_contract_symbol(contract: Contract) -> str:
    # Prioritize local symbol because for options, local symbol is OSI OCC code, but symbol is the underlying
    return contract.localSymbol or contract.symbol


def get_contract_symbol(contract: ContractDetails) -> str:
    return contract.contract.symbol


def get_detailed_contract_identifier(contract: ContractDetails) -> int:
    return contract.contract.conId


def get_contract_identifier(contract: Contract) -> int:
    if not contract.conId:
        print_error(f"Contract identifier is potentially erroneous - {contract.localSymbol}")
        return contract.conId

    return contract.conId


def get_incomplete_contract_identifier(contract: Contract):
    symbol = get_basic_contract_symbol(contract)
    exchange = contract.exchange
    type_ = contract.secType

    return f"{symbol}@{exchange}({type_})"
