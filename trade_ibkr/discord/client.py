import discord
from discord import Message

from trade_ibkr.utils import print_discord_log


class DiscordBot(discord.Client):
    async def on_ready(self):
        print_discord_log(f"Connected: {self.user}")

    async def on_message(self, message: Message):
        # Don't respond to ourselves
        if message.author == self.user:
            return

        await message.channel.send(message.content)
