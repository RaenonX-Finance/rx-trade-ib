from datetime import datetime
from typing import Callable

from trade_ibkr.model import OnExecutionFetchedGetParams, OnExecutionFetchedParams, PxData
from trade_ibkr.obj import IBapiInfo
from trade_ibkr.utils import get_detailed_contract_identifier


def request_earliest_execution_time(app: IBapiInfo, px_data_req_ids: list[int]) -> Callable[[], datetime]:
    def wrapper():
        return min(app.get_px_data_from_cache(req_id).earliest_time for req_id in px_data_req_ids)

    return wrapper


def get_execution_on_fetched_params(app: IBapiInfo, px_data_req_ids: list[int]) -> OnExecutionFetchedGetParams:
    def wrapper():
        px_data_list = [app.get_px_data_from_cache(req_id) for req_id in px_data_req_ids]

        return OnExecutionFetchedParams(
            earliest_time=min(px_data.earliest_time for px_data in px_data_list),
            contract_ids={px_data.contract_identifier for px_data in px_data_list}
        )

    return wrapper


def get_px_data_by_contract_identifier(
        app: IBapiInfo, px_data_req_ids: list[int], contract_identifier: int
) -> PxData:
    px_data = None
    for req_id in px_data_req_ids:
        data = app.get_px_data_from_cache(req_id)

        if get_detailed_contract_identifier(data.contract) == contract_identifier:
            px_data = data
            break

    return px_data
