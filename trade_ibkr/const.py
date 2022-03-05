from fastapi import FastAPI
from fastapi_socketio import SocketManager
from rich.console import Console

console = Console()
console_error = Console(stderr=True, style="bold red")

fast_api = FastAPI()
fast_api_socket = SocketManager(app=fast_api)

SR_PERIOD = 120
SR_MULTIPLIER = 1.2

AMPL_COEFF_TP = 2.2
AMPL_COEFF_SL = 1
