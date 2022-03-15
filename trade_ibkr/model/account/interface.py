from abc import ABC, abstractmethod
from decimal import Decimal
from typing import final

from ibapi.contract import Contract

from trade_ibkr.enums import OrderSideConst, Side, reverse_order_side
from trade_ibkr.utils import get_contract_identifier, print_log
from ..position import PositionData


class Account(ABC):
    @abstractmethod
    def get_current_position_data(self, contract_identifier: int) -> PositionData | None:
        """
        Get the current position data.

        Position could be 0 (neutral) if the financial instrument had been traded before or
        held over the day reset (5 PM CST for IBKR).

        Returns ``None`` if the financial instrument was not traded and not held.
        """
        raise NotImplementedError()

    def get_current_position_side(self, contract_identifier: int) -> Side:
        if not (position_data := self.get_current_position_data(contract_identifier)):
            return Side.NEUTRAL

        return position_data.side

    @final
    def long(self, contract: Contract, quantity: Decimal, *, px: float | None, message: str | None = None) -> bool:
        """
        Places a long order and return if an order to be placed.

        Does nothing if currently already have long positions.

        Reverses the positions if currently is shorting.
        """
        position_data = self.get_current_position_data(get_contract_identifier(contract))

        if position_data:
            match position_data.side:
                case Side.LONG:
                    return False
                case Side.SHORT:
                    quantity += abs(position_data.position)

        self.entry(contract, "BUY", quantity, px=px, message=message)
        return True

    @final
    def short(self, contract: Contract, quantity: Decimal, *, px: float | None, message: str | None = None) -> bool:
        """
        Places a short order and return if an order to be placed.

        Does nothing if currently already have short positions.

        Reverses the positions if currently is longing.
        """
        position_data = self.get_current_position_data(get_contract_identifier(contract))

        if position_data:
            match position_data.side:
                case Side.SHORT:
                    return False
                case Side.LONG:
                    quantity += abs(position_data.position)

        self.entry(contract, "SELL", quantity, px=px, message=message)
        return True

    def entry(
            self, contract: Contract, side: OrderSideConst, quantity: Decimal,
            *, px: float | None, message: str | None = None
    ):
        if message:
            print_log(f"[ORDER] {message}")

        self.place_order(contract, side, quantity, px)

    def exit(self, *, contract: Contract, px: float | None = None, message: str | None = None):
        position_data = self.get_current_position_data(get_contract_identifier(contract))

        if not position_data:
            return

        if message:
            print_log(f"[ORDER] {message}")

        self.place_order(contract, reverse_order_side(position_data.side.order_side), abs(position_data.position), px)

    @abstractmethod
    def place_order(self, contract: Contract, side: OrderSideConst, quantity: Decimal, px: float | None):
        raise NotImplementedError()
