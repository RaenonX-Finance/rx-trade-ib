import sys
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class PnL:
    unrealized: float = field(default=0)
    realized: float = field(default=0)

    def update(self, unrealized: float, realized: float):
        if unrealized != sys.float_info.max:  # Max value PnL means unavailable
            self.unrealized = unrealized
        if realized != sys.float_info.max:  # Max value PnL means unavailable
            self.realized = realized

    def __str__(self):
        return f"U [{self.unrealized:.2f}] R [{self.realized:.2f}]"
