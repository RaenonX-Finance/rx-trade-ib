from abc import ABC

from ibapi.contract import Contract, ContractDetails

from .common import IBapiBaseCommon


class IBapiBaseContract(IBapiBaseCommon, ABC):
    def __init__(self):
        super().__init__()

        self._contract_data: dict[int, ContractDetails | None] = {}

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)

        self._contract_data[reqId] = contractDetails

    def request_contract_data(self, contract: Contract) -> int:
        request_id = self.next_valid_request_id

        self.reqContractDetails(request_id, contract)

        return request_id
