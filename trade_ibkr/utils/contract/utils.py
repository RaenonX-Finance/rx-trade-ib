from ibapi.contract import Contract, ContractDetails

from ..log import print_error


def get_contract_symbol(contract: ContractDetails) -> str:
    return contract.contract.symbol


def get_detailed_contract_identifier(contract: ContractDetails) -> int:
    return contract.contract.conId


def get_contract_identifier(contract: Contract) -> int:
    if not contract.conId:
        print_error(f"Contract identifier is potentially erroneous - {contract.localSymbol}")
        return contract.conId

    return contract.conId
