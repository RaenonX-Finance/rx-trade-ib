from abc import ABC
from decimal import Decimal

from ibapi.contract import ContractDetails

from trade_ibkr.const import ACCOUNT_NUMBER_IN_USE
from trade_ibkr.model import OnPnLUpdated, OnPnLUpdatedEvent, PnL
from trade_ibkr.utils import asyncio_run, get_contract_symbol, get_detailed_contract_identifier, print_error, print_log
from .px import IBapiPx


class IBapiPnL(IBapiPx, ABC):
    def __init__(self):
        super().__init__()

        self._pnl_req_id_to_contract_req_id: dict[int, int] = {}
        self._pnl_of_contract_id: dict[int, PnL] = {}
        self._pnl_on_updated: OnPnLUpdated | None = None

    def request_pnl_single(self, contract_req_id: int, contract_details: ContractDetails):
        print_error("Check the PnL numbers before go live, the number seems to be problematic for futures.")

        req_id_pnl = self.next_valid_request_id
        self.reqPnLSingle(
            req_id_pnl,
            ACCOUNT_NUMBER_IN_USE,
            "",
            contract_details.contract.conId
        )
        self._pnl_req_id_to_contract_req_id[req_id_pnl] = contract_req_id
        self._pnl_of_contract_id[get_detailed_contract_identifier(contract_details)] = PnL()

        print_log(f"[TWS] Subscribe PnL of {get_contract_symbol(contract_details)}")

    def set_on_pnl_updated(self, on_pnl_updated: OnPnLUpdated):
        self._pnl_on_updated = on_pnl_updated

    def pnlSingle(
            self, reqId: int, pos: Decimal, dailyPnL: float,
            unrealizedPnL: float, realizedPnL: float, value: float
    ):
        super().pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)

        if not self._pnl_on_updated:
            print_error(
                "PnL updated, but no corresponding handler is set. "
                "Use `set_on_pnl_updated()` for setting it.",
            )
            return

        contract_req_id = self._pnl_req_id_to_contract_req_id[reqId]
        contract_data = self._contract_data[contract_req_id]

        if not contract_data:
            return

        self._pnl_of_contract_id[get_detailed_contract_identifier(contract_data)].update(unrealizedPnL, realizedPnL)

        async def execute_on_pnl_updated():
            # noinspection PyCallingNonCallable
            await self._pnl_on_updated(OnPnLUpdatedEvent(pnl_dict=self._pnl_of_contract_id))

        asyncio_run(execute_on_pnl_updated())
