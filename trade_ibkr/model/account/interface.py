from abc import ABC, abstractmethod
from decimal import Decimal
from typing import final

from ibapi.contract import Contract

from trade_ibkr.enums import Side, OrderSide
from ..position import PositionData
from ..action_status import ActionStatus


class Account(ABC):
    @abstractmethod
    def get_current_position_data(self, contract: Contract) -> PositionData | None:
        """
        Get the current position data.

        Position could be 0 (neutral) if the financial instrument had been traded before or
        held over the day reset (5 PM CT for IBKR).

        Returns ``None`` if the financial instrument was not traded and not held.
        """
        raise NotImplementedError()

    def get_current_position_side(self, contract: Contract) -> Side:
        if not (position_data := self.get_current_position_data(contract)):
            return Side.NEUTRAL

        return position_data.side

    @final
    def long(self, contract: Contract, quantity: Decimal, px: float, message: str | None = None) -> bool:
        """
        Places a long order and return if an order to be placed.

        Does nothing if currently already have long positions.

        Reverses the positions if currently is shorting.
        """
        position_data = self.get_current_position_data(contract)

        if position_data:
            match position_data.side:
                case Side.LONG:
                    return False
                case Side.SHORT:
                    quantity += abs(position_data.position)

        self.entry(contract, OrderSide.LONG, quantity, px, message)
        return True

    @final
    def short(self, contract: Contract, quantity: Decimal, px: float, message: str | None = None) -> bool:
        """
        Places a short order and return if an order to be placed.

        Does nothing if currently already have short positions.

        Reverses the positions if currently is longing.
        """
        position_data = self.get_current_position_data(contract)

        if position_data:
            match position_data.side:
                case Side.SHORT:
                    return False
                case Side.LONG:
                    quantity += abs(position_data.position)

        self.entry(contract, OrderSide.SHORT, quantity, px, message)
        return True

    def entry(
            self, contract: Contract, order_side: OrderSide, quantity: Decimal,
            px: float, message: str | None = None
    ):
        if message:
            print(message)

        self.place_order(contract, order_side, quantity, px)

    def exit(self, contract: Contract, px: float, message: str | None = None):
        position_data = self.get_current_position_data(contract)

        if not position_data:
            return

        if message:
            print(message)

        self.place_order(contract, position_data.side.order_side.reverse, abs(position_data.position), px)

    @abstractmethod
    def place_order(self, contract: Contract, order_side: OrderSide, quantity: Decimal, px: float):
        raise NotImplementedError()

    @property
    @abstractmethod
    def action_status(self) -> ActionStatus:
        raise NotImplementedError()
