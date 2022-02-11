from .px_data import IBapiInfoPxData
from .portfolio import IBapiInfoPortfolio


class IBapiInfo(IBapiInfoPxData, IBapiInfoPortfolio):
    pass
