import os

import uvicorn

from trade_ibkr.app import prepare_info_app
from trade_ibkr.const import fast_api

fast_api = fast_api  # Binding for `uvicorn`

prepare_info_app()

# Set current process to the highest priority
os.system(f"wmic process where processid={os.getpid()} CALL setpriority realtime")

if __name__ == "__main__":
    uvicorn.run("main:fast_api", host="127.0.0.1", port=8000)
