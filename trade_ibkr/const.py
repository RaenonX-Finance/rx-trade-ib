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
ACCOUNT_NUMBER_ACTUAL = config["system"]["account"]["actual"]

SR_PERIOD = config["support-resistance"]["period"]
SR_MULTIPLIER = config["support-resistance"]["multiplier"]

AMPL_COEFF_TP = config["risk-management"]["take-profit-ampl"]
AMPL_COEFF_SL = config["risk-management"]["stop-loss-ampl"]

MARKET_SOCKET_PATH = config["data"]["market"]

BOT_STRATEGY_CHECK_INTERVAL = config["bot"]["strategy-check-interval-sec"]
