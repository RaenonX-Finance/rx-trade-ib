from trade_ibkr.app import run_ib_server
from trade_ibkr.const import fast_api
from trade_ibkr.utils import set_current_process_to_highest_priority

fast_api = fast_api  # Binding for `uvicorn`

run_ib_server()
set_current_process_to_highest_priority()
