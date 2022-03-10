from abc import ABC, abstractmethod

from ibapi.contract import Contract, ContractDetails

from .base import IBapiBase


class IBapiContract(IBapiBase, ABC):
    def __init__(self):
        super().__init__()

        self._contract_data: dict[int, ContractDetails | None] = {}
        self._contract_request_source: dict[Contract, int] = {}

    def _is_same_contract(self, a: Contract, b: Contract) -> bool:
        return a.localSymbol == b.localSymbol

    def _get_req_id_of_source(self, source: Contract) -> int | None:
        for contract, req_id in self._contract_request_source.items():
            if self._is_same_contract(contract, source):
                return req_id

        return None

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)

        self._contract_data[reqId] = contractDetails

    def request_contract_data(self, contract: Contract) -> int:
        if existing_req_id := self._get_req_id_of_source(contract):
            return existing_req_id

        request_id = self.next_valid_request_id
        self._contract_request_source[contract] = request_id

        self.reqContractDetails(request_id, contract)

        return request_id
