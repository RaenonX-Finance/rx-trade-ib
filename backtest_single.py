import pandas as pd

from trade_ibkr.model import BacktestAccount, OnPxDataUpdatedEvent
from trade_ibkr.obj import start_app_backtest
from trade_ibkr.utils import make_futures_contract

app, thread = start_app_backtest(is_demo=True)

account = BacktestAccount()

contract = make_futures_contract("MNQH2", "GLOBEX")


@app.trade_on_px_data_backtest(
    account=account, contract=contract, duration="10 D", bar_size="1 min", min_data_rows=5
)
def main(e: OnPxDataUpdatedEvent):
    pass
    # simple_strategy(
    #     e.contract,
    #     e.account,
    #     e.px_data,
    #     attempt_enter=e.is_new_bar,
    #     quantity=Decimal(3)
    # )


pd.set_option(
    "display.max_rows", None,
    "display.max_columns", None,
    "display.width", None,
)

thread.join()

print(account.orders.dataframe)
