from trade_ibkr.app import prepare_info_app
from trade_ibkr.const import fast_api
from trade_ibkr.utils import set_current_process_to_highest_priority

fast_api = fast_api  # Binding for `uvicorn`

prepare_info_app()
set_current_process_to_highest_priority()
