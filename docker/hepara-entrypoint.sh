#!/bin/sh
set -eu

DATA_DIR=${HEPARA_DATA_DIR:-/app/data}
PDF_DIR=${PDF_PATH:-$DATA_DIR/pdf}
ADK_DIR=${HEPARA_ADK_DIR:-$DATA_DIR/.adk}
AUTHORS_DIR=${HEPARA_AUTHORS_DIR:-$DATA_DIR/.authors}
MCP_CONFIG=${MCP_PATH:-$DATA_DIR/mcp_config.json}
SKILL_DIR=${SKILL_PATH:-$DATA_DIR/skill}

normalize_env_value() {
    printf '%s' "$1" \
        | sed -e 's/^[[:space:]]*//' \
              -e 's/[[:space:]]#.*$//' \
              -e 's/[[:space:]]*$//' \
              -e 's/^"\(.*\)"$/\1/' \
              -e "s/^'\(.*\)'$/\1/"
}

OLLAMA_MODEL=$(normalize_env_value "${OLLAMA_MODEL:-llama3}")
if [ -z "$OLLAMA_MODEL" ]; then
    OLLAMA_MODEL=llama3
fi
if [ "${DISCORD_TOKEN+x}" = "x" ]; then
    DISCORD_TOKEN=$(normalize_env_value "$DISCORD_TOKEN")
fi

export HEPARA_DATA_DIR=$DATA_DIR
export PDF_PATH=$PDF_DIR
export MCP_PATH=$MCP_CONFIG
export SKILL_PATH=$SKILL_DIR
export HEPARA_SESSION_DB_URL=${HEPARA_SESSION_DB_URL:-sqlite+aiosqlite:///$ADK_DIR/adk_sessions.db}
export OLLAMA_HOST=${OLLAMA_HOST:-http://127.0.0.1:11434}
export OLLAMA_MODEL
export DISCORD_TOKEN

mkdir -p "$DATA_DIR" "$PDF_DIR" "$ADK_DIR" "$AUTHORS_DIR" "$(dirname "$MCP_CONFIG")" "$SKILL_DIR" /root/.ollama
touch "$MCP_CONFIG"

if [ -e /app/.adk ] && [ ! -L /app/.adk ]; then
    rm -rf /app/.adk
fi
ln -sfn "$ADK_DIR" /app/.adk
if [ -e /app/.authors ] && [ ! -L /app/.authors ]; then
    rm -rf /app/.authors
fi
ln -sfn "$AUTHORS_DIR" /app/.authors

ollama serve &
OLLAMA_PID=$!

for _ in $(seq 1 60); do
    if ollama list >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! ollama show "${OLLAMA_MODEL}" >/dev/null 2>&1; then
    ollama pull "${OLLAMA_MODEL}"
fi

trap 'kill "$OLLAMA_PID" 2>/dev/null || true' INT TERM EXIT

exec uv run "$@"
