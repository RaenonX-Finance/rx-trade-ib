from .make import make_crypto_contract, make_futures_contract, make_index_contract
from .type import ContractType, ContractMakerFunction

TYPE_TO_CONTRACT_FUNCTION: dict[ContractType, ContractMakerFunction] = {
    "Futures": make_futures_contract,
    "Index": make_index_contract,
    "Crypto": make_crypto_contract,
}
