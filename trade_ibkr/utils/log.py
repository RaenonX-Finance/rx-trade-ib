from datetime import datetime

from trade_ibkr.const import SUPPRESS_WARNINGS, console, console_error


def print_log(message: str):
    console.print(f"[green]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}[/green]: {message}")


def print_warning(message: str):
    if SUPPRESS_WARNINGS:
        return

    console.print(f"[yellow]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}: {message}[/yellow]")


def print_error(message: str):
    console_error.print(f"[red]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}[/red]: {message}")


def print_socket_event(event: str, additional: str = ""):
    message = f"[Socket] Received `[purple]{event}[/purple]`"

    if additional:
        message += f" - {additional}"

    print_log(message)
