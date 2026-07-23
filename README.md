# HEPARA Discord: High Energy Physics AI Research Assistant for Discord

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-google--adk-orange.svg)](https://github.com/google/adk)
[![Discord](https://img.shields.io/badge/interface-discord-5865F2.svg)](https://discord.com/developers/docs/intro)
[![Model](https://img.shields.io/badge/model-gemini--2.5--flash-purple.svg)](https://deepmind.google/technologies/gemini/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**HEPARA Discord** is a Discord bot interface for **HEPARA** (High Energy Physics AI Research Assistant), a specialized research companion for physicists working in High Energy Physics. Built on the **Google Agent Development Kit (ADK)** and powered by **Gemini**, the bot brings HEP literature tracking, citation monitoring, local paper analysis, PDG particle-data retrieval, optional MCP tools, and custom ADK skills directly into Discord conversations.

Mention the bot to ask research questions, continue saved reply-thread conversations, check arXiv updates, track author citations, query local papers, or route supported tasks through configured external tools.

---

## ✨ Features

-   **💬 Discord-Native Research Chat:**
    -   Start a conversation by mentioning the bot in a Discord channel.
    -   Continue the same saved conversation by replying to the bot thread.
    -   Automatically split long assistant responses to fit Discord message limits.
-   **📊 Citation Monitoring & Analysis:**
    -   Track author citation updates through INSPIRE-HEP.
    -   Store per-author citation snapshots for later comparison.
    -   Use Discord commands to inspect, add, remove, and refresh tracked authors.
-   **📑 arXiv Intelligence:**
    -   Search arXiv and INSPIRE-HEP from Discord.
    -   Fetch daily arXiv updates for configured categories.
    -   Rank daily papers by keyword matches and optional semantic relevance.
    -   Generate weekly trend recommendations with `arxivflow`.
-   **📚 Local Paper Q&A:**
    -   Download and ingest local PDFs under `PDF_PATH`.
    -   Generate Markdown sidecars when PDF extraction succeeds.
    -   Index papers with ChromaDB and answer questions against the local collection.
    -   Refresh the local paper database from Discord with `!update_db`.
-   **⚛️ PDG Particle Data:**
    -   Retrieve particle masses, decay widths, and lifetimes from the Particle Data Group database.
    -   Query decay channels and branching fractions, optionally filtered by requested decay products.
-   **🔌 Optional MCP Tools:**
    -   Add local command-based MCP servers through a user-managed `mcp_config.json`.
    -   HEPARA creates one MCP subagent per configured server and starts normally when MCP is not configured.
-   **🧩 External Skills:**
    -   Load custom Google ADK skill folders through `SKILL_PATH`.
    -   Create standalone skill subagents for skills that are not already attached to MCP servers.
-   **⏰ Scheduled Updates:**
    -   Configure daily and weekly arXiv update schedules.
    -   Send update results to a target Discord channel with `MAIN_CHANNEL_ID`.

## 🛠️ Tech Stack

-   **Framework:** [Google Agent Development Kit (ADK)](https://github.com/google/adk-python)
-   **Discord Interface:** [discord.py](https://discordpy.readthedocs.io/)
-   **Model:** Google Gemini (configurable, defaults to `gemini-2.5-flash`)
-   **Keyword Extraction:** [arXivFlow](https://github.com/zjzhao1002/arxivflow), with Ollama for local runs
-   **PDF Processing:** [PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) for Markdown extraction from downloaded PDFs
-   **Local Retrieval:** [ChromaDB](https://www.trychroma.com/) for querying downloaded arXiv papers
-   **Particle Data:** [pdg](https://github.com/particledatagroup/api) Python API for PDG particle properties and branching fractions
-   **External Tools:** [Model Context Protocol](https://modelcontextprotocol.io/) stdio servers configured by the user
-   **Data Sources:** INSPIRE-HEP API, arXiv API, Particle Data Group
-   **Environment:** Python 3.13+, [uv](https://github.com/astral-sh/uv)

## 🔗 Related Projects

-   [HEPARA](https://github.com/zjzhao1002/hepara): The original Streamlit and CLI research assistant.

---

## 🚀 Quick Start

### Docker Bot (Recommended)

The Discord bot is available as a Docker image at <https://hub.docker.com/r/zjzhao1002/hepara-discord>. The container includes the Python bot, Node.js/npm support for stdio MCP servers, and Ollama for local arXivFlow keyword extraction.

Pull the image:

```bash
docker pull zjzhao1002/hepara-discord:latest
```

Create the persistent app-data volume and a `hepara-ollama` volume for ollama models (You can reuse an existing `hepara-ollama` volume if you already run HEPARA locally):

```bash
docker volume create hepara-data
docker volume create hepara-ollama
```

Create a Docker env file with your Discord and Gemini credentials, then run:

```bash
docker run -d --name hepara-discord \
  --env-file .env \
  -v hepara-ollama:/root/.ollama \
  -v hepara-data:/app/data \
  zjzhao1002/hepara-discord:latest
```

The Docker image stores persistent bot data under `/app/data`, including saved Discord sessions, citation snapshots, local PDFs, generated Markdown sidecars, ChromaDB indexes, MCP configuration, and external skills. The first startup can take a while if Ollama needs to download the configured model.

Follow logs:

```bash
docker logs -f hepara-discord
```

### Source Bot

Clone the repository and install dependencies:

```bash
git clone https://github.com/zjzhao1002/hepara-discord.git
cd hepara-discord
uv sync
```

Copy the example environment file:

```bash
cp .env.example .env
```

Fill in your Discord bot token, Gemini API key, INSPIRE-HEP author name, target Discord channel, and tracking preferences. Then start the bot:

```bash
uv run python hepara-discord.py
```

---

## ⚙️ Installation

### Prerequisites

-   A Discord bot token from the Discord Developer Portal
-   A Google Gemini API key
-   Python 3.13 or higher and [uv](https://github.com/astral-sh/uv) for source-based local runs
-   [Docker](https://www.docker.com/) for the containerized bot
-   [Ollama](https://ollama.ai/) for local arXivFlow trend recommendations

### Discord Setup

In the Discord Developer Portal:

1.  Enable the **Message Content Intent** for the bot.
2.  Invite the bot to your server.
3.  Grant permissions to read messages, send messages, and reply in the target channels.
4.  Set `MAIN_CHANNEL_ID` to the channel where scheduled arXiv and citation updates should be posted.

### Environment Configuration

Create a `.env` file in the project root. Source runs can use quoted values through `python-dotenv`; Docker env files should use plain `KEY=value` lines without quotes.

```env
# Required
DISCORD_TOKEN=your_discord_bot_token
GOOGLE_API_KEY=your_google_api_key
AUTHOR="Your InspireHEP Author Name"

# Discord update destination
MAIN_CHANNEL_ID=your_discord_channel_id

# Model settings
GOOGLE_MODEL=gemini-2.5-flash

# Daily and weekly arXiv update schedule
TIMEZONE=Asia/Shanghai
DAILY_UPDATE_HOUR=9
DAILY_UPDATE_MINUTE=0
WEEKLY_UPDATE_HOUR=10
WEEKLY_UPDATE_MINUTE=0
WEEKLY_UPDATE_WEEKDAY=0

# arXiv daily updates and semantic filtering
CATEGORIES=hep-ph,hep-th,hep-ex
KEYWORDS="higgs phenomenology,dark matter,vector-like lepton,smeft"
DAILY_SEMANTIC_THRESHOLD=0.7
DAILY_SEMANTIC_MAX_RESULTS=10

# Weekly arXiv trend recommendations
ARXIVFLOW_KEYWORD_BACKEND=ollama
OLLAMA_MODEL=llama3.1

# Local paper storage and integrations
PDF_PATH=pdf
MCP_PATH=mcp_config.json
SKILL_PATH=skill
```

For Docker, the image sets these storage defaults:

```text
HEPARA_DATA_DIR=/app/data
PDF_PATH=/app/data/pdf
HEPARA_SESSION_DB_URL=sqlite+aiosqlite:////app/data/.adk/adk_sessions.db
MCP_PATH=/app/data/mcp_config.json
SKILL_PATH=/app/data/skill
OLLAMA_HOST=http://127.0.0.1:11434
```

The Docker volumes preserve local state across container restarts:

-   `hepara-data` stores the saved ADK session database, citation records, downloaded PDFs, generated Markdown sidecars, Chroma index, MCP config, and skill folders under `/app/data`.
-   `hepara-ollama` stores downloaded Ollama models under `/root/.ollama`.

### Optional MCP Servers and Skills

Copy the example MCP config and edit it with local stdio MCP servers you want HEPARA Discord to use:

```bash
cp mcp_config.example.json mcp_config.json
```

The supported format is:

```json
{
  "mcpServers": {
    "server_name": {
      "command": "command-to-run",
      "args": ["optional", "arguments"],
      "env": {"OPTIONAL_VARIABLE": "value"}
    }
  }
}
```

`args` and `env` may be omitted. Missing and empty configuration files simply disable MCP support; malformed files produce a warning without preventing the bot from starting.

Set `SKILL_PATH` to a directory containing ADK skill folders. MCP-specific skills should use folder names that exactly match MCP server names in `mcp_config.json`. Skill folders that do not match MCP server names become standalone skill subagents under `skills_agent`.

After MCP or skills are configured, use `!mcp` and `!skill` in Discord to list what is available. Restart the bot after changing MCP configuration or skill folders.

---

## 🏃 Usage

### Discord Chat

Mention the bot in a channel:

```text
@HEPARA find recent Higgs boson papers
@HEPARA what are my latest citation updates?
@HEPARA summarize arXiv:2401.00001
@HEPARA what is the mass of the Z boson?
```

Each bot mention starts or resumes a conversation scoped by channel and root message. Replies to the bot continue the same saved conversation. Session history is stored in `.adk/adk_sessions.db` for source runs and `/app/data/.adk/adk_sessions.db` in Docker.

### Prefix Commands

HEPARA Discord uses `!` prefix commands, not Discord-native slash commands:

<!-- ```text
!help
!mcp
!skill
!paper
!update_db
!author
!add_author Albert.Einstein.1
!rm_author Albert.Einstein.1
!citation
!category
!add_category hep-ph
!rm_category hep-ph
!arxiv_daily
!arxiv_weekly
!keyword
!add_keyword dark matter
!rm_keyword dark matter
``` -->

-   `!help` shows the command list.
-   `!mcp` lists available MCP servers.
-   `!skill` lists available skills.
-   `!paper` lists local papers available for analysis.
-   `!update_db` refreshes the local paper database.
-   `!author`, `!add_author`, and `!rm_author` inspect and manage tracked INSPIRE-HEP authors.
-   `!citation` checks citation updates for tracked authors.
-   `!category`, `!add_category`, and `!rm_category` manage arXiv categories for tracking and recommendations.
-   `!arxiv_daily` fetches tracked arXiv category updates and ranks papers by keyword and semantic relevance.
-   `!arxiv_weekly` fetches weekly arXiv trend recommendations.
-   `!keyword`, `!add_keyword`, and `!rm_keyword` manage the daily arXiv keyword filter.

Daily arXiv filtering deduplicates papers across tracked `CATEGORIES`, matches comma-separated `KEYWORDS` against RSS titles and abstracts, and ranks exact title/abstract matches above semantic-only matches. If `GOOGLE_API_KEY` is set, the daily update can also add high-similarity semantic matches from ChromaDB/Gemini embeddings. Tune semantic inclusion with `DAILY_SEMANTIC_THRESHOLD`; higher values are stricter.

### Local Papers

Set `PDF_PATH` to the directory containing local PDFs. The bot can convert PDFs to Markdown, index them in ChromaDB, and answer questions against the local paper collection. If `PDF_PATH` is not set, the default local directory is `pdf/`.

Use `!paper` to list indexed papers and `!update_db` to refresh the local paper database.

### Docker Operations

Stop and remove the container:

```bash
docker rm -f hepara-discord
```

Restart while keeping persistent state:

```bash
docker run -d --name hepara-discord \
  --env-file .env \
  -v hepara-ollama:/root/.ollama \
  -v hepara-data:/app/data \
  zjzhao1002/hepara-discord:latest
```

Build the image from source:

```bash
docker build -t hepara-discord .
```

See [docker/README.md](docker/README.md) for local image testing, Docker Hub publishing, multi-platform builds, and troubleshooting.

---

## 🧑‍💻 Development

Run the test suite:

```bash
uv run python -m unittest discover -s tests
```

Compile-check the source:

```bash
uv run python -m compileall hepara-discord.py hepara utils tests
```

General Discord commands live in `hepara/bot_commands.py` as a `commands.Cog`; scheduled arXiv update commands live with their task Cog in `hepara/bot_tasks.py`. Add new `@commands.command(...)` methods to the relevant Cog so `hepara/bot.py` can keep `setup_hook()` focused on registering command groups.

## 📄 License

See [LICENSE](LICENSE).
