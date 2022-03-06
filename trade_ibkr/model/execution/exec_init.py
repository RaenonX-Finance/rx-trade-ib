from collections import defaultdict
from decimal import Decimal
from typing import DefaultDict, Iterable

from trade_ibkr.utils import get_contract_identifier
from .model import GroupedOrderExecution, OrderExecution
from .type import OrderExecutionGroupKey


def init_grouped_executions(order_execs: Iterable[OrderExecution]) -> DefaultDict[int, list[GroupedOrderExecution]]:
    ret = defaultdict(list)

    grouped_executions: DefaultDict[OrderExecutionGroupKey, list[OrderExecution]] = defaultdict(list)
    for execution in order_execs:
        key = (
            execution.order_id,
            execution.side,
            get_contract_identifier(execution.contract),
        )
        grouped_executions[key].append(execution)

    # Do not activate the tracker for the 1st execution as it might start with existing position
    position_tracker: dict[int, Decimal] = {}
    for key, grouped in sorted(
            grouped_executions.items(),
            key=lambda item: min(execution.time for execution in item[1])
    ):
        _, _, contract_identifier = key

        grouped_execution = GroupedOrderExecution.from_executions(grouped)

        if grouped_execution.realized_pnl:
            if contract_identifier not in position_tracker:
                # Activate tracker
                position_tracker[contract_identifier] = Decimal(0)
            else:
                position = position_tracker[contract_identifier]

                # Position reduced or zero-ed
                if position and grouped_execution.quantity > abs(position):
                    # Position reversed
                    closing, opening = grouped_execution.to_closing_and_opening(abs(position))

                    # --- Append closing execution
                    ret[contract_identifier].append(closing)
                    # --- Append opening (reversed) execution
                    ret[contract_identifier].append(opening)

                    position_tracker[contract_identifier] = position + grouped_execution.signed_quantity
                    continue

                position_tracker[contract_identifier] += grouped_execution.signed_quantity
        elif contract_identifier in position_tracker:
            # Tracking positions
            position_tracker[contract_identifier] += grouped_execution.signed_quantity

        ret[contract_identifier].append(grouped_execution)

    return ret
