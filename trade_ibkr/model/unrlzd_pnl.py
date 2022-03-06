from dataclasses import dataclass, field


@dataclass(kw_only=True)
class UnrealizedPnL:
    min: float = field(default=0)
    current: float = field(default=0)
    max: float = field(default=0)

    def __add__(self, other: "UnrealizedPnL"):
        if not isinstance(other, UnrealizedPnL):
            raise ValueError(f"`UnrealizedPnL` can only add with another `UnrealizedPnL` (other type: {type(other)}")

        return UnrealizedPnL(
            min=self.min + other.min,
            current=self.current + other.current,
            max=self.max + other.max
        )

    def update(self, pnl: float):
        self.min = min(pnl, self.min)
        self.current = pnl
        self.max = max(pnl, self.max)
