from .components import IBapiError, IBapiPx, IBapiOrderManagement


class IBapiServer(IBapiPx, IBapiOrderManagement, IBapiError):
    pass
