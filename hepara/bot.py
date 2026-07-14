import discord
from pathlib import Path
from discord.ext import commands
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai.types import Content, Part 
from .agent import hep_coordinator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSION_DB_DIR = PROJECT_ROOT / ".adk"
SESSION_DB_URL = f"sqlite+aiosqlite:///{SESSION_DB_DIR}/adk_sessions.db"
MAX_DISCORD_MESSAGE_LENGTH = 1900

class HeparaDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="/",
            description="A Discord Bot for HEPARA.",
            intents=intents
        )

        SESSION_DB_DIR.mkdir(parents=True, exist_ok=True)
        session_service = DatabaseSessionService(db_url=SESSION_DB_URL)
        self.runner = Runner(app_name="HEPARA", agent=hep_coordinator, session_service=session_service)
    
    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        if self.user and self.user in message.mentions:
            prompt = message.clean_content.replace(f"@{self.user.display_name}", "").strip()
            if not prompt:
                prompt = "Say hello and introduce what you can do."
            
            user_id = self.get_discord_user_id(message)
            session_id = await self.ensure_discord_session(message)
            async with message.channel.typing():
                content = Content(role="user", parts=[Part(text=prompt)])
                async for response in self.runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                    if response.content and response.content.parts and response.author != "user":
                        for part in response.content.parts:
                            if part.text:
                                await self.reply_discord_text(message, part.text)
        
        await self.process_commands(message)

    def get_discord_user_id(self, message: discord.Message) -> str:
        return f"discord-user-{message.author.id}"

    def get_discord_session_id(self, message: discord.Message) -> str:
        return f"discord-{message.channel.id}-{message.author.id}"
    
    async def ensure_discord_session(self, message: discord.Message) -> str:
        user_id = self.get_discord_user_id(message)
        session_id = self.get_discord_session_id(message)
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id=user_id,
                session_id=session_id,
            )
        return session_id
    
    def split_discord_message(self, text: str, limit: int = MAX_DISCORD_MESSAGE_LENGTH) -> list[str]:
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

    async def reply_discord_text(self, message: discord.Message, text: str) -> None:
        for chunk in self.split_discord_message(text):
            await message.reply(chunk, mention_author=False)
