import discord
from pathlib import Path
from discord.ext import commands
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai.types import Content, Part 
from .agent import hep_coordinator
from .bot_commands import HeparaCommands
from .bot_tasks import HeparaTasks

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SESSION_DB_DIR = PROJECT_ROOT / ".adk"
SESSION_DB_URL = f"sqlite+aiosqlite:///{SESSION_DB_DIR}/adk_sessions.db"
MAX_DISCORD_MESSAGE_LENGTH = 1900

class HeparaDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix="!",
            help_command=None,
            description="A Discord Bot for HEPARA.",
            intents=intents
        )

        SESSION_DB_DIR.mkdir(parents=True, exist_ok=True)
        session_service = DatabaseSessionService(db_url=SESSION_DB_URL)
        self.runner = Runner(app_name="HEPARA", agent=hep_coordinator, session_service=session_service)
        self.discord_reply_roots: dict[int, int] = {}

    async def setup_hook(self):
        await self.add_cog(HeparaCommands())
        await self.add_cog(HeparaTasks(self))
    
    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        root_message_id = await self.get_discord_root_message_id(message)
        if root_message_id is not None:
            prompt = self.get_discord_prompt(message)
            if not prompt:
                prompt = "Say hello and introduce what you can do."
            
            user_id = self.get_discord_user_id(message, root_message_id)
            session_id = await self.ensure_discord_session(message, root_message_id)
            async with message.channel.typing():
                content = Content(role="user", parts=[Part(text=prompt)])
                async for response in self.runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                    if response.content and response.content.parts and response.author != "user":
                        for part in response.content.parts:
                            if part.text:
                                await self.reply_discord_text(message, part.text, root_message_id)
        
        await self.process_commands(message)

    def get_discord_prompt(self, message: discord.Message) -> str:
        prompt = message.clean_content
        if self.user and self.user in message.mentions:
            prompt = prompt.replace(f"@{self.user.display_name}", "")
        return prompt.strip()

    async def get_discord_root_message_id(self, message: discord.Message) -> int | None:
        if self.user and self.user in message.mentions:
            return message.id

        referenced_message = await self.get_referenced_message(message)
        if not referenced_message or not self.is_discord_bot_message(referenced_message):
            return None

        return await self.get_discord_reply_root_message_id(referenced_message)

    def is_discord_bot_message(self, message: discord.Message) -> bool:
        return bool(self.user and message.author.id == self.user.id)

    async def get_discord_reply_root_message_id(self, message: discord.Message) -> int | None:
        visited_message_ids = set()
        current_message = message
        fallback_message_id = None

        while current_message and current_message.id not in visited_message_ids:
            visited_message_ids.add(current_message.id)

            if current_message.id in self.discord_reply_roots:
                return self.discord_reply_roots[current_message.id]

            reference = current_message.reference
            if not reference or reference.message_id is None:
                break

            fallback_message_id = reference.message_id
            parent_message = await self.get_referenced_message(current_message)
            if parent_message is None:
                break

            if self.user and self.user in parent_message.mentions:
                return parent_message.id

            current_message = parent_message

        return fallback_message_id

    async def get_referenced_message(self, message: discord.Message) -> discord.Message | None:
        if not message.reference:
            return None

        resolved_message = getattr(message.reference, "resolved", None)
        if isinstance(resolved_message, discord.Message):
            return resolved_message

        if message.reference.message_id is None:
            return None

        try:
            return await message.channel.fetch_message(message.reference.message_id)
        except discord.DiscordException:
            return None

    def get_discord_user_id(self, message: discord.Message, root_message_id: int) -> str:
        return f"discord-conversation-{message.channel.id}-{root_message_id}"

    def get_discord_session_id(self, message: discord.Message, root_message_id: int) -> str:
        return f"discord-{message.channel.id}-{root_message_id}"
    
    async def ensure_discord_session(self, message: discord.Message, root_message_id: int) -> str:
        user_id = self.get_discord_user_id(message, root_message_id)
        session_id = self.get_discord_session_id(message, root_message_id)
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

    async def reply_discord_text(self, message: discord.Message, text: str, root_message_id: int) -> None:
        for chunk in self.split_discord_message(text):
            reply = await message.reply(chunk, mention_author=False)
            self.discord_reply_roots[reply.id] = root_message_id
