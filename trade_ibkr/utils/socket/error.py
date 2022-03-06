import json
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from trade_ibkr.model import OnErrorEvent


class ErrorMessage(TypedDict):
    message: str


def to_socket_message_error(error_event: "OnErrorEvent") -> str:
    data: ErrorMessage = {
        "message": str(error_event),
    }

    return json.dumps(data)
