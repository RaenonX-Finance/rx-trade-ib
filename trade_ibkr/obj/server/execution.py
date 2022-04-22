from abc import ABC

import pandas as pd

from trade_ibkr.const import SERVER_CLIENT_ID_DEMO, SERVER_CLIENT_ID_LIVE
from trade_ibkr.model import OnExecutionFetchedEvent, OnExecutionFetchedGetParams
from trade_ibkr.utils import print_log
from .components import IBapiExecution
from ...enums import ExecutionDataCol


class IBapiExecutionRecorder(IBapiExecution, ABC):
    def __init__(
            self, *,
            is_demo: bool | None = None, client_id: int | None = None
    ):
        super().__init__()

        self.activate(
            8384 if is_demo else 8383,  # Configured at TWS
            client_id or (SERVER_CLIENT_ID_LIVE if is_demo else SERVER_CLIENT_ID_DEMO)
        )

    async def _unaggregated_fetch(self, e: OnExecutionFetchedEvent):
        for identifier, df in e.executions.execution_dataframes.items():
            dest = f"execution-{identifier}.csv"
            print_log(f"Saved to: {dest}")
            df.to_csv(dest, index=False)

        self.disconnect()

    async def _aggregated_fetch(self, e: OnExecutionFetchedEvent):
        df = pd.concat(e.executions.execution_dataframes.values())
        df.sort_values(by=[ExecutionDataCol.EPOCH_SEC], inplace=True)

        dest = f"executions-aggregated.csv"
        print_log(f"Saved to: {dest}")
        df.to_csv(dest, index=False)

        self.disconnect()

    def store_executions(
            self, on_execution_fetched_params: OnExecutionFetchedGetParams, *,
            aggregate: bool = False
    ):
        self.set_on_executions_fetched(
            on_execution_fetched=self._aggregated_fetch if aggregate else self._unaggregated_fetch,
            on_execution_fetched_params=on_execution_fetched_params
        )
        self.request_all_executions()
