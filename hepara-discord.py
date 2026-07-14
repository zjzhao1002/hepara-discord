import os
import asyncio
import discord
import logging
from discord.ext import commands
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

AUTHOR=os.getenv('AUTHOR')

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai.types import Content, Part 
from utils.mcp_helpers import print_mcp_servers
from utils.skill_helpers import print_skills
from utils.paper_helpers import update_database, print_papers
from hepara.agent import hep_coordinator
from hepara.subagents.inspirehep_agent.tools import track_citations_updates

SESSION_DB_DIR = Path(".adk")
SESSION_DB_URL = "sqlite+aiosqlite:///./.adk/adk_sessions.db"
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MAX_DISCORD_MESSAGE_LENGTH = 2000

SESSION_DB_DIR.mkdir(parents=True, exist_ok=True)
session_service = DatabaseSessionService(db_url=SESSION_DB_URL)

runner = Runner(app_name="HEPARA", agent=hep_coordinator, session_service=session_service)

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="/",
    description="A Discord Bot of HEPARA",
    intents=intents
)

def get_discord_user_id(message: discord.Message) -> str:
    return f"discord-user-{message.author.id}"

def get_discord_session_id(message: discord.Message) -> str:
    return f"discord-{message.channel.id}-{message.author.id}"

async def ensure_discord_session(message: discord.Message) -> str:
    user_id = get_discord_user_id(message)
    session_id = get_discord_session_id(message)
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )
    return session_id

def split_discord_message(text: str, limit: int = MAX_DISCORD_MESSAGE_LENGTH) -> list[str]:
    if limit <= 0:
        raise ValueError("Discord message limit must be positive.")

    chunks = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break

        window = remaining[:limit]
        split_at = max(
            window.rfind("\n\n"),
            window.rfind("\n"),
            window.rfind(" "),
        )
        if split_at <= 0:
            split_at = limit

        chunk = remaining[:split_at].rstrip()
        chunks.append(chunk or remaining[:limit])
        remaining = remaining[split_at:].lstrip()

    return chunks

async def reply_discord_text(message: discord.Message, text: str) -> None:
    for chunk in split_discord_message(text):
        await message.reply(chunk, mention_author=False)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    if bot.user and bot.user in message.mentions:
        prompt = message.clean_content.replace(f"@{bot.user.display_name}", "").strip()
        if not prompt:
            prompt = "Say hello and introduce what you can do."
        
        user_id = get_discord_user_id(message)
        session_id = await ensure_discord_session(message)
        async with message.channel.typing():
            content = Content(role="user", parts=[Part(text=prompt)])
            async for response in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                if response.content and response.content.parts and response.author != "user":
                    for part in response.content.parts:
                        if part.text:
                            await reply_discord_text(message, part.text)
    
    await bot.process_commands(message)


if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set. Add it to the .env file")

bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)
