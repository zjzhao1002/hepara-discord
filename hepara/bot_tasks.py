import os
import asyncio
import discord
import feedparser
import datetime as dt
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING, List, Dict
from discord.ext import commands, tasks

if TYPE_CHECKING:
    from hepara.bot import HeparaDiscordBot

BASE_URL = "https://rss.arxiv.org/rss/"
ARXIV_TIMEZONE = ZoneInfo(os.getenv("ARXIV_TIMEZONE", "Asia/Shanghai"))
ARXIV_UPDATE_TIME = dt.time(
    hour=int(os.getenv("ARXIV_UPDATE_HOUR", "9")),
    minute=int(os.getenv("ARXIV_UPDATE_MINUTE", "0")),
    tzinfo=ARXIV_TIMEZONE,
)
ARXIV_MAX_RESULTS = 10

def get_arxiv_updates() -> List[Dict]:
    categories = os.getenv("CATEGORIES")
    if not categories:
        return []
    
    all_updates = []
    categories_list = categories.split(sep=",")
    for category in categories_list:
        category_articles = _get_category_update(category.strip())
        all_updates.append({"Category": category.strip(), "Articles": category_articles})
    return all_updates

def _get_category_update(category: str) -> List[Dict]:
    url = BASE_URL + category.strip()
    feed = feedparser.parse(url)

    entries = feed.entries
    articles = []
    for entry in entries:
        if "Announce Type: new" in entry.description:
            articles.append({
                'title': entry.title,
                'authors': entry.author,
                'link': entry.link
            })
    
    return articles

def format_arxiv_update(all_updates: List[Dict]) -> str:
    if not all_updates:
        return "No arXiv updates found."
    
    formated_results = ""
    for update in all_updates:
        category = update['Category']
        articles = update['Articles']
        formated_update = _format_category_update(articles=articles, category=category)
        formated_results += f"{formated_update}\n"
    return formated_results

def _format_category_update(articles: List[Dict], category: str, max_results: int=ARXIV_MAX_RESULTS) -> str:
    if not articles:
        return f"No arXiv {category} updates found."

    lines = [f"arXiv {category} update: {len(articles)} article(s) found."]
    for article in articles[:max_results]:
        lines.append(
            "\n".join(
                [
                    f"- {article['title']}",
                    f"  Authors: {article['authors']}",
                    f"  {article['link']}",
                ]
            )
        )

    remaining = len(articles) - max_results
    if remaining > 0:
        lines.append(f"...and {remaining} more.")

    return "\n\n".join(lines)

class HeparaTasks(commands.Cog):
    def __init__(self, bot: "HeparaDiscordBot") -> None:
        self.bot = bot
        self.daily_arxiv_update.start()

    async def fetch_arxiv_update(self) -> List[Dict]:
        return await asyncio.to_thread(get_arxiv_updates)

    async def send_arxiv_update(
        self,
        destination: discord.abc.Messageable
    ):
        articles = await self.fetch_arxiv_update()
        message = format_arxiv_update(articles)
        for chunk in self.bot.split_discord_message(message):
            await destination.send(chunk)

    @tasks.loop(time=ARXIV_UPDATE_TIME)
    async def daily_arxiv_update(self):
        channel_id = os.getenv("MAIN_CHANNEL_ID")
        if not channel_id:
            print("Main Channel ID is unknown; skipping daily arXiv update.")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            channel = await self.bot.fetch_channel(int(channel_id))

        await self.send_arxiv_update(channel) # type: ignore

    @daily_arxiv_update.before_loop
    async def before_daily_arxiv_update(self):
        await self.bot.wait_until_ready()

    @daily_arxiv_update.error # type: ignore
    async def on_daily_arxiv_update_error(self, error: Exception):
        print(f"Daily arXiv update failed: {error}")

    @commands.command(name="arxiv_update", description="Get the arXiv daily updates") # type: ignore
    async def arxiv_update(self, ctx: commands.Context):
        async with ctx.typing():
            try:
                articles = await self.fetch_arxiv_update()
            except Exception as exc:
                await ctx.send(f"Sorry, I could not fetch arXiv updates: {exc}")
                return

        message = format_arxiv_update(articles)
        for chunk in self.bot.split_discord_message(message):
            await ctx.send(chunk)
