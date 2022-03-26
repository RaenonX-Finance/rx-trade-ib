from trade_ibkr.const import LINE_TOKEN
from .client import LineNotifyClient

line_notify = LineNotifyClient(token=LINE_TOKEN)
