from ibapi.client import EClient
from ibapi.contract import Contract, ContractDetails
from ibapi.wrapper import EWrapper


class IBapiInfoBase(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

        self._contract_data: dict[int, ContractDetails | None] = {}

        # Start from 1 to avoid false-negative
        self._request_id = 1

    @property
    def next_valid_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        self._contract_data[reqId] = contractDetails

    def _request_contract_data(self, contract: Contract) -> int:
        request_id = self.next_valid_request_id

        self.reqContractDetails(request_id, contract)

        return request_id
