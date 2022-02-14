import threading
import time
from typing import Callable, TypeVar, Union

from .api import IBapiBot, IBapiInfo


T = TypeVar("T", bound=Union[IBapiInfo | IBapiBot])


def init_app(app_callable: Callable[[], T], is_demo: bool = False) -> tuple[T, threading.Thread]:
    app = app_callable()
    app.connect("localhost", 8384 if is_demo else 8383, 0)

    def run_loop():
        try:
            app.run()
        except Exception as ex:
            app.disconnect()
            raise ex

    api_thread = threading.Thread(target=run_loop)
    api_thread.start()

    while not app.isConnected():
        time.sleep(0.1)

    return app, api_thread


def start_app(*, is_demo: bool = False) -> tuple[IBapiBot, threading.Thread]:
    return init_app(IBapiBot, is_demo)


def start_app_info(*, is_demo: bool = False) -> tuple[IBapiInfo, threading.Thread]:
    return init_app(IBapiInfo, is_demo)
