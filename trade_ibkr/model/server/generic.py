from dataclasses import dataclass
from typing import Any, Callable, Coroutine, TypeAlias


@dataclass(kw_only=True)
class OnErrorEvent:
    code: int
    message: str

    def __str__(self):
        return f"[{self.code}] {self.message}"


OnError: TypeAlias = Callable[[OnErrorEvent], Coroutine[Any, Any, None]]
