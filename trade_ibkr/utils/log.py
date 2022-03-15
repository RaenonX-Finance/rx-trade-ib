from datetime import datetime

from trade_ibkr.const import console, console_error


def print_log(message: str):
    console.print(f"[green]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}[/green]: {message}")


def print_warning(message: str):
    console.print(f"[yellow]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}: {message}[/yellow]")


def print_error(message: str):
    console_error.print(f"[red]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}[/red]: {message}")
