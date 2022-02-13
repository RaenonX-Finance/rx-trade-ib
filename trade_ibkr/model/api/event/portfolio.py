from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from ...position import Position


@dataclass(kw_only=True)
class OnPositionFetchedEvent:
    position: Position


OnPositionFetched = Callable[[OnPositionFetchedEvent], Coroutine[Any, Any, None]]
