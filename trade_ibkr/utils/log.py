from datetime import datetime


def print_log(message: str):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]}: {message}")
