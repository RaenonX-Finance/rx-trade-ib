import asyncio

from trade_ibkr.const import DISCORD_TOKEN
from .client import DiscordBot


def run_discord_bot() -> DiscordBot:
    client = DiscordBot()

    asyncio.create_task(client.start(DISCORD_TOKEN))

    return client
