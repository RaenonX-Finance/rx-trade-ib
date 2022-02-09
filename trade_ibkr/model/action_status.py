from dataclasses import dataclass


@dataclass
class ActionStatus:
    order_pending: bool = False
    order_executed_on_current_k: bool = False
