# HEPARA Discord

HEPARA Discord is a Discord bot for HEPARA, a High Energy Physics research assistant built with Google ADK. It lets users mention the bot in Discord to search papers, track citations, analyze local papers, query PDG particle data, and route supported tasks through optional MCP servers or custom skills.

## Features

- Discord mention-based chat with persistent per-user, per-channel sessions.
- arXiv and INSPIRE-HEP paper search, citation lookup, and citation update tracking.
- Local PDF ingestion and ChromaDB-backed paper question answering.
- PDG particle mass, width, lifetime, decay, and branching-fraction lookup.
- Optional MCP server and ADK skill integrations.
- Prefix commands for listing local resources and refreshing the paper database.
- Long Discord responses are split automatically to fit Discord message limits.

## Requirements

- Python 3.13 or newer
- A Discord bot token
- A Google API key for Gemini-backed ADK agents and embeddings
- Optional: Ollama for local keyword extraction in paper trend recommendations

## Installation

```bash
git clone https://github.com/zjzhao1002/hepara-discord.git
cd hepara-discord
uv sync
```

## Configuration

Create a `.env` file in the project root:

```bash
DISCORD_TOKEN=your_discord_bot_token
GOOGLE_API_KEY=your_google_api_key
AUTHOR="Your InspireHEP Author Name"

# Optional
GOOGLE_MODEL=gemini-2.5-flash
PDF_PATH=pdf
CATEGORIES=hep-ph,hep-ex
ARXIVFLOW_KEYWORD_BACKEND=ollama
OLLAMA_MODEL=llama3.1
MCP_PATH=mcp_config.json
SKILL_PATH=skill
```

In the Discord Developer Portal, enable the Message Content Intent for the bot. Invite the bot to your server with permissions to read messages and send replies.

## Usage

Start the Discord bot:

```bash
uv run python hepara-discord.py
```

Mention the bot in a channel:

```text
@HEPARA find recent Higgs boson papers
@HEPARA what are my latest citation updates?
@HEPARA summarize arXiv:2401.00001
@HEPARA what is the mass of the Z boson?
```

Session history is stored in `.adk/adk_sessions.db` and is scoped by Discord channel and user.

### Commands

HEPARA uses `!` prefix commands, not Discord-native slash commands:

```text
!help
!mcp
!skill
!paper
!update_db
!arxiv_update
```

- `!help` shows the command list.
- `!mcp` lists available MCP servers.
- `!skill` lists available skills.
- `!paper` lists local papers available for analysis.
- `!update_db` refreshes the local paper database.
- `!arxiv_update` fetches the latest tracked arXiv category updates.

## Local Papers

Set `PDF_PATH` to the directory containing local PDFs. The bot can convert PDFs to Markdown, index them in ChromaDB, and answer questions against the local paper collection. If `PDF_PATH` is not set, the default local directory is `pdf/`. Use `!paper` to list indexed papers and `!update_db` to refresh the local paper database.

## Optional Integrations

MCP servers can be configured with `MCP_PATH`, which should point to a JSON file containing an `mcpServers` object. Custom ADK skills can be loaded from `SKILL_PATH`. Use `!mcp` and `!skill` in Discord to list what is available.

## Adding Commands

General Discord commands live in `hepara/bot_commands.py` as a `commands.Cog`; scheduled arXiv update commands live with their task Cog in `hepara/bot_tasks.py`. Add new `@commands.command(...)` methods to the relevant Cog so `hepara/bot.py` can keep `setup_hook()` focused on registering command groups.

## Development

Run the test suite:

```bash
uv run python -m unittest discover -s tests
```

Compile-check the source:

```bash
uv run python -m compileall hepara-discord.py hepara utils tests
```

## License

See [LICENSE](LICENSE).
