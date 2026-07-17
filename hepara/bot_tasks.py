import os
import asyncio
import discord
import feedparser
import datetime as dt
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING, List, Dict
from discord.ext import commands, tasks
from hepara.subagents.arxiv_agent.tools import recommend_by_trends

if TYPE_CHECKING:
    from hepara.bot import HeparaDiscordBot

BASE_URL = "https://rss.arxiv.org/rss/"
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Shanghai"))
DAILY_UPDATE_TIME = dt.time(
    hour=int(os.getenv("DAILY_UPDATE_HOUR", "9")),
    minute=int(os.getenv("DAILY_UPDATE_MINUTE", "0")),
    tzinfo=TIMEZONE,
)
WEEKLY_UPDATE_TIME = dt.time(
    hour=int(os.getenv("WEEKLY_UPDATE_HOUR", "10")),
    minute=int(os.getenv("WEEKLY_UPDATE_MINUTE", "0")),
    tzinfo=TIMEZONE
)
WEEKLY_UPDATE_WEEKDAY = int(os.getenv("WEEKLY_UPDATE_WEEKDAY", "0"))
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

def format_daily_update(all_updates: List[Dict]) -> str:
    if not all_updates:
        return "No arXiv updates found."
    
    formatted_results = ""
    for update in all_updates:
        category = update['Category']
        articles = update['Articles']
        formatted_update = _format_category_update(articles=articles, category=category)
        formatted_results += f"{formatted_update}\n"
    return formatted_results

def _format_category_update(articles: List[Dict], category: str, max_results: int=ARXIV_MAX_RESULTS) -> str:
    if not articles:
        return f"No arXiv {category} updates found."

    lines = [f"arXiv {category} update: {len(articles)} article(s) found."]
    for article in articles[:max_results]:
        all_authors = [a.strip() for a in article["authors"].split(",") if a.strip()]
        if len(all_authors) > 3:
            authors = ", ".join(all_authors[:3])
            authors += " et al., "
        else:
            authors = article["authors"] + ", "
        lines.append(
            "\n".join(
                [
                    f"- {article['title']}",
                    f"  Authors: {authors}",
                    f"  {article['link']}",
                ]
            )
        )

    remaining = len(articles) - max_results
    if remaining > 0:
        lines.append(f"...and {remaining} more.")

    return "\n\n".join(lines)

def format_weekly_update(update: Dict) -> str:
    if not update:
        return "No weekly arXiv trend update found."

    if "error" in update:
        return update["error"]

    keywords = update.get("keywords", {})
    papers = update.get("papers", [])
    sections = ["Weekly arXiv trend update"]

    if keywords:
        keyword_lines = ["Trending keywords:"]
        for keyword, count in keywords.items():
            keyword_lines.append(f"- {keyword}: {count}")
        sections.append("\n".join(keyword_lines))
    else:
        sections.append("No trending keywords found.")

    if papers:
        paper_lines = ["Recommended papers:"]
        for paper in papers:
            title = paper.get("title", "No Title")
            authors = paper.get("authors", "No Author")
            arxiv_id = paper.get("arxiv_id", "N/A")
            paper_lines.append(
                "\n".join(
                    [
                        f"- {title}",
                        f"  Authors: {authors}",
                        f"  arXiv ID: {arxiv_id}",
                    ]
                )
            )
        sections.append("\n\n".join(paper_lines))
    else:
        sections.append("No recommended papers found.")

    return "\n\n".join(sections)

class HeparaTasks(commands.Cog):
    def __init__(self, bot: "HeparaDiscordBot") -> None:
        self.bot = bot
        self.daily_arxiv_update.start()
        self.weekly_arxiv_update.start()

    async def fetch_daily_update(self) -> List[Dict]:
        return await asyncio.to_thread(get_arxiv_updates)

    async def send_daily_update(
        self,
        destination: discord.abc.Messageable
    ):
        articles = await self.fetch_daily_update()
        message = format_daily_update(articles)
        for chunk in self.bot.split_discord_message(message):
            await destination.send(chunk)

    async def send_weekly_update(
        self,
        destination: discord.abc.Messageable
    ):
        articles = await recommend_by_trends()
        message = format_weekly_update(articles)
        for chunk in self.bot.split_discord_message(message):
            await destination.send(chunk)

    @tasks.loop(time=DAILY_UPDATE_TIME)
    async def daily_arxiv_update(self):
        channel_id = os.getenv("MAIN_CHANNEL_ID")
        if not channel_id:
            print("Main Channel ID is unknown; skipping daily arXiv update.")
            return
        
        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            channel = await self.bot.fetch_channel(int(channel_id))

        await self.send_daily_update(channel) # type: ignore

    @daily_arxiv_update.before_loop
    async def before_daily_arxiv_update(self):
        await self.bot.wait_until_ready()

    @daily_arxiv_update.error # type: ignore
    async def on_daily_arxiv_update_error(self, error: Exception):
        print(f"Daily arXiv update failed: {error}")

    @commands.command(name="arxiv_daily", description="Get the arXiv daily updates") # type: ignore
    async def arxiv_daily(self, ctx: commands.Context):
        async with ctx.typing():
            try:
                articles = await self.fetch_daily_update()
            except Exception as exc:
                await ctx.send(f"Sorry, I could not fetch arXiv updates: {exc}")
                return

        message = format_daily_update(articles)
        for chunk in self.bot.split_discord_message(message):
            await ctx.send(chunk)

    @tasks.loop(time=WEEKLY_UPDATE_TIME)
    async def weekly_arxiv_update(self):
        now = dt.datetime.now(TIMEZONE)
        if now.weekday() != WEEKLY_UPDATE_WEEKDAY:
            return

        channel_id = os.getenv("MAIN_CHANNEL_ID")
        if not channel_id:
            print("Main Channel ID is unknown; skipping weekly arXiv update.")
            return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            channel = await self.bot.fetch_channel(int(channel_id))

        await self.send_weekly_update(channel) # type: ignore

    @weekly_arxiv_update.before_loop
    async def before_weekly_arxiv_update(self):
        await self.bot.wait_until_ready()

    @weekly_arxiv_update.error # type: ignore
    async def on_weekly_arxiv_update_error(self, error: Exception):
        print(f"Weekly arXiv update failed: {error}")

    @commands.command(name="arxiv_weekly", description="Get the arXiv weekly recommendations") # type: ignore
    async def arxiv_weekly(self, ctx: commands.Context):
        async with ctx.typing():
            try:
                articles = await recommend_by_trends()
            except Exception as exc:
                await ctx.send(f"Sorry, I could not fetch arXiv updates: {exc}")
                return

        message = format_weekly_update(articles)
        for chunk in self.bot.split_discord_message(message):
            await ctx.send(chunk)
