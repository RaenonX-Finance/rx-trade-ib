from datetime import datetime
from typing import Callable

from trade_ibkr.const import LINE_ENABLE
from trade_ibkr.model import OnExecutionFetchedGetParams, OnExecutionFetchedParams, PxData
from trade_ibkr.obj import IBapiServer
from trade_ibkr.utils import get_detailed_contract_identifier, print_warning


def request_earliest_execution_time(app: IBapiServer, px_data_req_ids: list[int]) -> Callable[[], datetime]:
    def wrapper():
        return min(app.get_px_data_from_cache(req_id).earliest_time for req_id in px_data_req_ids)

    return wrapper


def get_execution_on_fetched_params(app: IBapiServer, px_data_req_ids: list[int]) -> OnExecutionFetchedGetParams:
    def wrapper():
        return OnExecutionFetchedParams(
            px_data_list=[app.get_px_data_from_cache(req_id) for req_id in px_data_req_ids]
        )

    return wrapper


def get_px_data_by_contract_identifier(
        app: IBapiServer, px_data_req_ids: list[int], contract_identifier: int, period_sec: int,
) -> PxData:
    px_data = None
    for req_id in px_data_req_ids:
        data = app.get_px_data_from_cache(req_id)

        if get_detailed_contract_identifier(data.contract) == contract_identifier and data.period_sec == period_sec:
            px_data = data
            break

    return px_data


def show_warnings_as_needed(*, is_demo: bool):
    if not LINE_ENABLE:
        print_warning("LINE Px reporting not enabled.", force=True)

    if is_demo:
        print_warning("Using demo environment.", force=True)
