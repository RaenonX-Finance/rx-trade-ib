from datetime import datetime

from trade_ibkr.const import SUPPRESS_WARNINGS, console, console_error


def print_log(message: str, *, timestamp_color: str = "green"):
    console.print(
        f"[{timestamp_color}]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}[/{timestamp_color}]: "
        f"{message}"
    )


def print_warning(message: str, *, force: bool = False):
    if SUPPRESS_WARNINGS and not force:
        return

    console.print(f"[yellow]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}: {message}[/yellow]")


def print_error(message: str):
    console_error.print(f"[red]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}[/red]: {message}")


def print_socket_event(event: str, additional: str = ""):
    message = f"[Socket] Received `[purple]{event}[/purple]`"

    if additional:
        message += f" - {additional}"

    print_log(message)


def print_line_log(message: str):
    print_log(f"[LINE] {message}", timestamp_color="blue")
