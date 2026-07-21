# HEPARA Discord Docker Image

This Docker image runs the HEPARA Discord bot with its Python dependencies, Node.js/npm support for stdio MCP servers, and a local Ollama server in the same container.

Use this image when you want the Discord bot to stay online with persistent session history, citation-tracking records, local paper indexes, MCP configuration, skills, and Ollama models.

Source code and documentation are available in the GitHub repository: [zjzhao1002/hepara-discord](https://github.com/zjzhao1002/hepara-discord).

## Image Contents

- HEPARA Discord bot entrypoint: `hepara-discord.py`
- arXiv, INSPIRE-HEP, FAQ, PDG, MCP, and skills agents
- Python dependencies installed with `uv`
- `node`, `npm`, and `npx` copied from the official Node image stage
- Ollama for local arXivFlow keyword extraction and trend recommendations
- Persistent volume paths for bot data and Ollama models

## Configuration

Create a Docker env file before running the container. Docker env files should use plain `KEY=value` lines without quotes.

```env
DISCORD_TOKEN=your_discord_bot_token
GOOGLE_API_KEY=your_google_api_key
AUTHOR=Your InspireHEP Author Name
MAIN_CHANNEL_ID=your_discord_channel_id

GOOGLE_MODEL=gemini-2.5-flash
CATEGORIES=hep-ph,hep-th,hep-ex
KEYWORDS=higgs phenomenology,dark matter,vector-like lepton,smeft
TIMEZONE=Asia/Shanghai
DAILY_UPDATE_HOUR=9
DAILY_UPDATE_MINUTE=0
WEEKLY_UPDATE_HOUR=10
WEEKLY_UPDATE_MINUTE=0
WEEKLY_UPDATE_WEEKDAY=0

ARXIVFLOW_KEYWORD_BACKEND=ollama
OLLAMA_MODEL=llama3
```

The container sets these storage defaults:

```text
HEPARA_DATA_DIR=/app/data
PDF_PATH=/app/data/pdf
HEPARA_SESSION_DB_URL=sqlite+aiosqlite:////app/data/.adk/adk_sessions.db
MCP_PATH=/app/data/mcp_config.json
SKILL_PATH=/app/data/skill
OLLAMA_HOST=http://127.0.0.1:11434
```

The entrypoint normalizes `DISCORD_TOKEN` and `OLLAMA_MODEL` so accidental quotes or inline comments in the env file do not break Discord login or Ollama model pulls.

## Volumes

Use two named Docker volumes:

- `hepara-ollama`: the volume for Ollama models, mounted at `/root/.ollama`
- `hepara-data`: app-data volume, mounted at `/app/data`

Create these volumes:

```bash
docker volume create hepara-ollama
docker volume create hepara-data
```

The `hepara-data` volume stores:

- Discord conversation session database: `/app/data/.adk/adk_sessions.db`
- Per-author citation snapshots: `/app/data/.authors`
- Downloaded PDFs and generated Markdown sidecars: `/app/data/pdf`
- ChromaDB local paper index: `/app/data/pdf/chroma_db`
- MCP configuration: `/app/data/mcp_config.json`
- External skills: `/app/data/skill`

The container symlinks `/app/.adk` and `/app/.authors` into `/app/data`, so app code that expects repo-root state still uses persistent storage.

## Build

Run from the repository root:

```bash
docker build -t hepara-discord .
```

For a clean rebuild:

```bash
docker build --no-cache -t hepara-discord .
```

## Run

Run the bot with your env file and volumes:

```bash
docker run -d --name hepara-discord \
  --env-file .env \
  -v hepara-ollama:/root/.ollama \
  -v hepara-data:/app/data \
  hepara-discord
```

Follow logs:

```bash
docker logs -f hepara-discord
```

Stop and remove the container:

```bash
docker rm -f hepara-discord
```

Restart with a rebuilt image while keeping all persistent state:

```bash
docker rm -f hepara-discord

docker run -d --name hepara-discord \
  --env-file .env \
  -v hepara-ollama:/root/.ollama \
  -v hepara-data:/app/data \
  hepara-discord
```

## Discord Setup

In the Discord Developer Portal:

1. Enable the Message Content Intent for the bot.
2. Invite the bot to your server.
3. Grant permissions to read messages, send messages, and reply in the target channels.

Mention the bot in Discord to start a conversation. Replies to the bot continue the same saved conversation thread.

HEPARA uses `!` prefix commands:

```text
!help
!mcp
!skill
!paper
!update_db
!author
!add_author
!rm_author
!citation
!arxiv_daily
!arxiv_weekly
!keyword
!add_keyword dark matter
!rm_keyword dark matter
```

## Optional MCP And Skills

The container creates an empty MCP config at:

```text
/app/data/mcp_config.json
```

It should contain an `mcpServers` object when MCP servers are enabled. Example:

```json
{
  "mcpServers": {
    "memory_server": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

External ADK skills should be copied into:

```text
/app/data/skill
```

Because `/app/data` is a volume, MCP configuration and skills survive container replacement.

## Publish

Log in to Docker Hub:

```bash
docker login
```

Tag and push a local image:

```bash
docker tag hepara-discord your-dockerhub-username/hepara-discord:latest
docker push your-dockerhub-username/hepara-discord:latest
```

For a version tag:

```bash
docker tag hepara-discord your-dockerhub-username/hepara-discord:0.1.0
docker push your-dockerhub-username/hepara-discord:0.1.0
```

For a multi-platform build:

```bash
docker buildx create --use

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-dockerhub-username/hepara-discord:latest \
  --push .
```
