from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from ...position import Position


@dataclass(kw_only=True)
class OnPositionFetchCompletedEvent:
    position: Position


OnPositionFetchCompleted = Callable[[Position], Coroutine[Any, Any, None]]
