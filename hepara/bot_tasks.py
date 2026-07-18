import os
import re
import asyncio
import chromadb
import discord
import feedparser
import datetime as dt
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING, Any, List, Dict
from discord.ext import commands, tasks
from chromadb.utils import embedding_functions
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
DAILY_SEMANTIC_MAX_RESULTS = int(os.getenv("DAILY_SEMANTIC_MAX_RESULTS", str(ARXIV_MAX_RESULTS)))
DAILY_SEMANTIC_THRESHOLD = float(os.getenv("DAILY_SEMANTIC_THRESHOLD", "0.35"))

def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()

def _get_keywords() -> List[str]:
    keywords = os.getenv("KEYWORDS")
    if not keywords:
        return []

    return [
        _normalize_text(keyword)
        for keyword in keywords.split(",")
        if keyword.strip()
    ]

def _get_categories() -> List[str]:
    categories = os.getenv("CATEGORIES")
    if not categories:
        return []

    deduped_categories = []
    seen_categories = set()
    for category in categories.split(","):
        normalized_category = category.strip()
        if not normalized_category or normalized_category in seen_categories:
            continue

        deduped_categories.append(normalized_category)
        seen_categories.add(normalized_category)

    return deduped_categories

def _matches_keywords(article: Dict, keywords: List[str]) -> bool:
    if not keywords:
        return True

    searchable_text = _normalize_text(
        f"{article.get('title', '')} {article.get('abstract', '')}"
    )
    return any(keyword in searchable_text for keyword in keywords)

def _article_id(article: Dict, fallback: str) -> str:
    arxiv_id = str(article.get("arxiv_id") or "").strip()
    if arxiv_id and arxiv_id != "Unknown ID":
        return arxiv_id

    link = str(article.get("link") or "").strip()
    return link or fallback

def _annotate_article(article: Dict, score: float, reason: str) -> Dict:
    annotated = dict(article)
    annotated["relevance_score"] = max(float(annotated.get("relevance_score", 0.0)), score)
    reasons = list(annotated.get("relevance_reasons", []))
    if reason not in reasons:
        reasons.append(reason)
    annotated["relevance_reasons"] = reasons
    return annotated

def _filter_articles_by_keywords(articles: List[Dict]) -> List[Dict]:
    keywords = _get_keywords()
    if not keywords:
        return articles

    return [
        _annotate_article(article, 1.0, "keyword match")
        for article in articles
        if _matches_keywords(article, keywords)
    ]

def _get_chroma_collection(document_embedding):
    client = chromadb.Client()
    return client.get_or_create_collection(
        name = "arxiv_daily",
        metadata={"hnsw:space": "cosine"},
        embedding_function=document_embedding # type: ignore
    )

def _get_embedding_function(task_type: str):
    return embedding_functions.GoogleGeminiEmbeddingFunction(
        model_name="gemini-embedding-001",
        api_key_env_var="GOOGLE_API_KEY",
        task_type=task_type,
    )

def _cosine_distance_to_similarity(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance))

def _vector_search(articles: List[Dict]) -> Dict[str, Any]:
    keywords = _get_keywords()
    if not articles or not keywords or not os.getenv("GOOGLE_API_KEY"):
        return {}

    document_embedding = _get_embedding_function("RETRIEVAL_DOCUMENT")
    query_embedding = _get_embedding_function("RETRIEVAL_QUERY")
    collection = _get_chroma_collection(document_embedding)

    documents = []
    metadatas = []
    ids = []

    for idx, article in enumerate(articles):
        document = _normalize_text(
            f"{article.get('title', '')} {article.get('abstract', '')}"
        )
        if not document:
            continue

        documents.append(document)

        article_id = _article_id(article, f"{article.get('category', 'daily')}-{idx}")
        ids.append(article_id)

        metadata = {
            "arxiv_id": article.get("arxiv_id", "Unknown ID"),
            "authors": article.get("authors", "Unknown author"),
            "title": article.get("title", "Untitled"),
        }
        metadatas.append(metadata)

    if not documents:
        return {}

    collection.upsert(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )

    query_embeddings = query_embedding(keywords)
    return collection.query(
        query_embeddings=query_embeddings,
        n_results=min(DAILY_SEMANTIC_MAX_RESULTS, len(documents)),
        include=["metadatas", "distances"],
    ) # type: ignore

def _semantic_matches_from_query_results(
    articles: List[Dict],
    query_results: Dict[str, Any],
    threshold: float=DAILY_SEMANTIC_THRESHOLD
) -> List[Dict]:
    articles_by_id = {
        _article_id(article, f"{article.get('category', 'daily')}-{idx}"): article
        for idx, article in enumerate(articles)
    }
    matches: Dict[str, Dict] = {}

    result_ids = query_results.get("ids") or []
    result_distances = query_results.get("distances") or []
    for ids_for_query, distances_for_query in zip(result_ids, result_distances):
        for article_id, distance in zip(ids_for_query, distances_for_query):
            article = articles_by_id.get(article_id)
            if not article:
                continue

            similarity = _cosine_distance_to_similarity(float(distance))
            if similarity < threshold:
                continue

            current = matches.get(article_id, article)
            matches[article_id] = _annotate_article(
                current,
                similarity,
                f"semantic match {similarity:.2f}",
            )

    return sorted(
        matches.values(),
        key=lambda article: article.get("relevance_score", 0.0),
        reverse=True,
    )

def _merge_relevant_articles(keyword_matches: List[Dict], semantic_matches: List[Dict]) -> List[Dict]:
    merged: Dict[str, Dict] = {}
    for idx, article in enumerate(keyword_matches + semantic_matches):
        article_id = _article_id(article, f"{article.get('category', 'daily')}-{idx}")
        if article_id in merged:
            existing = merged[article_id]
            merged[article_id] = _annotate_article(
                existing,
                article.get("relevance_score", 0.0),
                ", ".join(article.get("relevance_reasons", [])),
            )
        else:
            merged[article_id] = article

    return sorted(
        merged.values(),
        key=lambda article: article.get("relevance_score", 0.0),
        reverse=True,
    )

def _filter_relevant_articles(articles: List[Dict]) -> List[Dict]:
    keyword_matches = _filter_articles_by_keywords(articles)
    try:
        query_results = _vector_search(articles)
        semantic_matches = _semantic_matches_from_query_results(articles, query_results)
    except Exception as exc:
        print(f"Daily arXiv semantic search failed: {exc}")
        semantic_matches = []

    return _merge_relevant_articles(keyword_matches, semantic_matches)

def _merge_article_categories(existing_article: Dict, new_article: Dict) -> Dict:
    merged_article = dict(existing_article)
    categories = list(merged_article.get("categories", []))
    for category in new_article.get("categories", [new_article.get("category")]):
        if category and category not in categories:
            categories.append(category)

    merged_article["categories"] = categories
    merged_article["category"] = ", ".join(categories)
    return merged_article

def _deduplicate_articles_by_arxiv_id(articles: List[Dict]) -> List[Dict]:
    deduped_articles: Dict[str, Dict] = {}
    for idx, article in enumerate(articles):
        article_id = _article_id(article, f"{article.get('category', 'daily')}-{idx}")
        normalized_article = dict(article)
        category = normalized_article.get("category")
        normalized_article["categories"] = list(normalized_article.get("categories", []))
        if category and category not in normalized_article["categories"]:
            normalized_article["categories"].append(category)

        if article_id in deduped_articles:
            deduped_articles[article_id] = _merge_article_categories(
                deduped_articles[article_id],
                normalized_article,
            )
        else:
            deduped_articles[article_id] = normalized_article

    return list(deduped_articles.values())

def _get_abstract(description: str) -> str:
    return '\n'.join(description.splitlines()[1:])

def _remove_arxiv_version(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id)

def _get_arxiv_id(link: str, description: str) -> str:
    link_match = re.search(r"/abs/([^?#]+)", link)
    if link_match:
        return _remove_arxiv_version(link_match.group(1))

    desc_match = re.search(r"arXiv:([^\s]+)", description)
    return _remove_arxiv_version(desc_match.group(1)) if desc_match else "Unknown ID"

def get_arxiv_updates() -> List[Dict]:
    categories_list = _get_categories()
    if not categories_list:
        return []
    
    all_category_articles = []
    for category in categories_list:
        all_category_articles.extend(_get_category_update(category))

    deduped_articles = _deduplicate_articles_by_arxiv_id(all_category_articles)
    filtered_articles = _filter_relevant_articles(deduped_articles)
    return [{"Category": ", ".join(categories_list), "Articles": filtered_articles}]

def _get_category_update(category: str) -> List[Dict]:
    url = BASE_URL + category.strip()
    feed = feedparser.parse(url)

    entries = feed.entries
    articles = []
    for entry in entries:
        if "Announce Type: new" in entry.description:
            abstract = _get_abstract(entry.description) # type: ignore
            arxiv_id = _get_arxiv_id(entry.link, entry.description) # type: ignore
            articles.append({
                'title': entry.title,
                'authors': entry.author,
                'arxiv_id': arxiv_id,
                'category': category,
                'abstract': abstract,
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
        relevance = ""
        if "relevance_score" in article:
            reasons = ", ".join(article.get("relevance_reasons", []))
            relevance = f"  Relevance: {article['relevance_score']:.2f}"
            if reasons:
                relevance += f" ({reasons})"

        article_lines = [
            f"- {article['title']}",
            f"  Authors: {authors}",
        ]
        if relevance:
            article_lines.append(relevance)
        if article.get("categories"):
            article_lines.append(f"  Categories: {', '.join(article['categories'])}")
        article_lines.append(f"  {article['link']}")
        lines.append(
            "\n".join(article_lines)
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
