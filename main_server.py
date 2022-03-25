import uvicorn

from trade_ibkr.app import run_ib_server
from trade_ibkr.const import fast_api
from trade_ibkr.discord import run_discord_bot
from trade_ibkr.utils import set_current_process_to_highest_priority


# Discord bot have to wait until fast api has been started
# > https://gist.github.com/haykkh/49ed16a9c3bbe23491139ee6225d6d09
@fast_api.on_event("startup")
async def startup_event():
    discord_bot = run_discord_bot()
    run_ib_server(discord_bot=discord_bot)
    set_current_process_to_highest_priority()


if __name__ == '__main__':
    uvicorn.run("main_server:fast_api", port=8002)
