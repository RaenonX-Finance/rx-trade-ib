from enum import Enum, auto


class FetchStatus(Enum):
    NOT_FETCHED = auto()
    FETCHING = auto()
    COMPLETED = auto()
