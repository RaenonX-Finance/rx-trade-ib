from decimal import Decimal

from ibapi.contract import Contract

from trade_ibkr.enums import OrderSide
from .interface import Account
from ..action_status import ActionStatus
from ..order import BacktestOrderEntry, Orders
from ..position import Position, PositionData


class BacktestAccount(Account):
    def __init__(self):
        self._position: Position = Position([])

        self._order_multiplier: float | None = None
        self._order_history: list[BacktestOrderEntry] = []

        self._action_status: ActionStatus = ActionStatus()

    def get_current_position_data(self, contract: Contract) -> PositionData | None:
        return self._position.get_position_data(contract)

    def place_order(self, contract: Contract, order_side: OrderSide, quantity: Decimal, px: float):
        current_position_data = self._position.get_position_data(contract)

        if not current_position_data:
            position_data = PositionData(
                contract=contract,
                position=quantity * order_side.multiplier,
                avg_cost=px,
            )
        else:
            new_position = current_position_data.position + quantity * order_side.multiplier

            total_cost = (
                    current_position_data.total_cost +
                    quantity * order_side.multiplier * Decimal(contract.multiplier) * Decimal(px)
            )

            position_data = PositionData(
                contract=contract,
                position=new_position,
                avg_cost=float(total_cost / new_position) if new_position != 0 else 0,
            )

        if not self._order_multiplier:
            self._order_multiplier = float(contract.multiplier)

        self._order_history.append(BacktestOrderEntry(
            side=order_side,
            quantity=quantity,
            px=px,
        ))
        self._position.update_position(position_data)

    @property
    def action_status(self) -> ActionStatus:
        return self._action_status

    @property
    def orders(self) -> Orders:
        return Orders(self._order_multiplier, self._order_history)
