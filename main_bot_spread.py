import os

from trade_ibkr.app import prepare_bot_app_spread

prepare_bot_app_spread()

# Set current process to the highest priority
os.system(f"wmic process where processid={os.getpid()} CALL setpriority realtime")
