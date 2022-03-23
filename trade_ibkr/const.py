from fastapi import FastAPI
from fastapi_socketio import SocketManager
from rich.console import Console
import yaml

console = Console()
console_error = Console(stderr=True, style="bold red")

fast_api = FastAPI()
fast_api_socket = SocketManager(app=fast_api)

# ------ Load config

with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)
    # Print current config
    console.print("[cyan]--- Config content ---[/cyan]")
    console.print(yaml.dump(config, default_flow_style=False))

IS_DEMO = config["system"]["demo"]
ACCOUNT_NUMBER_DEMO = config["system"]["account"]["demo"]
ACCOUNT_NUMBER_LIVE = config["system"]["account"]["live"]
ACCOUNT_NUMBER_IN_USE = ACCOUNT_NUMBER_DEMO if IS_DEMO else ACCOUNT_NUMBER_LIVE

RISK_MGMT_TP_X = config["risk-management"]["take-profit-x"]
RISK_MGMT_SL_X = config["risk-management"]["stop-loss-x"]

SR_MULTIPLIER = config["sr-level"]["multiplier"]
SR_STRONG_THRESHOLD = config["sr-level"]["strong-threshold"]

MARKET_TREND_WINDOW = config["data"]["trend-window"]

DIFF_TREND_WINDOW = config["data"]["diff-sma-window"]
DIFF_TREND_WINDOW_DEFAULT = DIFF_TREND_WINDOW["default"]

SMA_PERIODS = config["data"]["sma"]

BOT_STRATEGY_CHECK_INTERVAL = config["bot"]["strategy-check-interval-sec"]
BOT_POSITION_FETCH_INTERVAL = config["bot"]["position-fetch-interval-sec"]

POSITION_ON_FIRST_REALIZED = {
    int(identifier): int(position)
    for identifier, position
    in config["server"]["position-on-first-realized"].items()
}

SERVER_CONTRACTS = config["server"]["contract"]
SERVER_CLIENT_ID_LIVE = config["server"]["client-id"]["live"]
SERVER_CLIENT_ID_DEMO = config["server"]["client-id"]["demo"]
