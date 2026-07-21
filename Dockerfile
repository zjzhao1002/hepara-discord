FROM node:22-bookworm-slim AS node-runtime

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    HEPARA_DATA_DIR=/app/data \
    PDF_PATH=/app/data/pdf \
    HEPARA_SESSION_DB_URL=sqlite+aiosqlite:////app/data/.adk/adk_sessions.db \
    MCP_PATH=/app/data/mcp_config.json \
    SKILL_PATH=/app/data/skill \
    ARXIVFLOW_KEYWORD_BACKEND=ollama \
    OLLAMA_HOST=http://127.0.0.1:11434 \
    OLLAMA_MODEL=llama3

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git zstd \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

RUN pip install --no-cache-dir uv \
    && curl -fsSL https://ollama.com/install.sh | sh

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen \
    && chmod +x docker/hepara-entrypoint.sh

VOLUME ["/app/data", "/root/.ollama"]

ENTRYPOINT ["docker/hepara-entrypoint.sh"]
CMD ["python", "hepara-discord.py"]
