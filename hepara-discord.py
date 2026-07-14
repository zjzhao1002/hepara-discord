import os
import logging
from dotenv import load_dotenv

load_dotenv()

AUTHOR=os.getenv('AUTHOR')
DISCORD_TOKEN=os.getenv('DISCORD_TOKEN')

from hepara.bot import HeparaDiscordBot

def main():
    handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
    bot = HeparaDiscordBot()

    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set. Add it to the .env file")

    bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)

if __name__ == "__main__":
    main()
