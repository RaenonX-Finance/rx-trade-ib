from typing import DefaultDict, Iterable, TYPE_CHECKING

from pandas import DataFrame

from trade_ibkr.utils import print_log
from .df_init import init_exec_dataframe
from .exec_init import init_grouped_executions
from .model import GroupedOrderExecution, OrderExecution

if TYPE_CHECKING:
    from trade_ibkr.model import OnExecutionFetchedParams


class OrderExecutionCollection:
    def _init_exec_dataframe(self, params: "OnExecutionFetchedParams"):
        for identifier, grouped_executions in self._executions.items():
            if identifier not in params.contract_ids:
                # Skip contract IDs not to be included
                continue

            self._executions_dataframe[identifier] = init_exec_dataframe(
                grouped_executions,
                # Equity doesn't have multiplier
                multiplier=float(grouped_executions[0].contract.multiplier or 1),
                px_data=params.px_data_dict_execution_period_sec[identifier],
            )

    def __init__(self, order_execs: Iterable[OrderExecution], params: "OnExecutionFetchedParams"):
        self._executions: DefaultDict[int, list[GroupedOrderExecution]] = init_grouped_executions(order_execs)

        self._executions_dataframe: dict[int, DataFrame] = {}
        self._init_exec_dataframe(params)

    @property
    def executions(self) -> dict[int, list[GroupedOrderExecution]]:
        return self._executions

    def save_executions(self):
        for identifier, exec_df in self._executions_dataframe.items():
            exec_df.to_csv(f"data-{identifier}.csv")
            print_log(f"[yellow]Executions of identifier {identifier} saved.[/yellow]")

    @property
    def execution_dataframes(self) -> dict[int, DataFrame]:
        return self._executions_dataframe
