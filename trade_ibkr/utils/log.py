from datetime import datetime

from trade_ibkr.const import console


def print_log(message: str):
    console.print(f"[green]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}[/green]: {message}")
