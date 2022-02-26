from fastapi import FastAPI
from fastapi_socketio import SocketManager
from rich.console import Console

console = Console()

fast_api = FastAPI()
fast_api_socket = SocketManager(app=fast_api)

SR_PERIOD = 60
SR_MULTIPLIER = 1.2
