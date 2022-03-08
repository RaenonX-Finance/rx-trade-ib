from .px_data import PxDataCol


class PxDataPairSuffix:
    ON_HI = "_hi"
    ON_LO = "_lo"


class PxDataPairCol:
    DATE = PxDataCol.DATE

    CLOSE_HI = f"close{PxDataPairSuffix.ON_HI}"
    CLOSE_LO = f"close{PxDataPairSuffix.ON_LO}"

    SPREAD = "spread"

    SPREAD_LO = "spread_lo"
    SPREAD_MID = "spread_mid"
    SPREAD_HI = "spread_hi"
