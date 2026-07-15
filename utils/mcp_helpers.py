import os
import json
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
def get_mcp_path() -> Path:
    configured_path = os.getenv("MCP_PATH")
    if configured_path:
        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path
    return PROJECT_ROOT / "mcp_config.json"

def read_mcp_servers(filename: str | Path) -> Dict[str, Any]:
    path = Path(filename)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.info("MCP configuration %s does not exist; MCP is disabled.", path)
        return {}
    except OSError as exc:
        logger.warning("Could not read MCP configuration %s: %s", path, exc)
        return {}

    if not content.strip():
        logger.info("MCP configuration %s is empty; MCP is disabled.", path)
        return {}

    try:
        config = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON in MCP configuration %s: %s", path, exc)
        return {}

    if config == {}:
        logger.info("MCP configuration %s is empty; MCP is disabled.", path)
        return {}
    if not isinstance(config, dict):
        logger.warning("MCP configuration %s must be a JSON object.", path)
        return {}

    servers = config.get("mcpServers")
    if servers is None:
        logger.warning(
            "MCP configuration %s must contain an 'mcpServers' object.", path
        )
        return {}
    if not isinstance(servers, dict):
        logger.warning("'mcpServers' in %s must be a JSON object.", path)
        return {}
    if not servers:
        logger.info("MCP configuration %s has no servers; MCP is disabled.", path)
        return {}

    return servers

def validate_mcp_server(name: str, server: Any) -> bool:
    if not name.strip():
        logger.warning("Skipping MCP server with an empty name.")
        return False
    if not isinstance(server, dict):
        logger.warning("Skipping MCP server %r: configuration must be an object.", name)
        return False

    command = server.get("command")
    if not isinstance(command, str) or not command.strip():
        logger.warning("Skipping MCP server %r: 'command' must be a non-empty string.", name)
        return False

    args = server.get("args", [])
    if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        logger.warning("Skipping MCP server %r: 'args' must be an array of strings.", name)
        return False

    env = server.get("env")
    if env is not None and (
        not isinstance(env, dict)
        or not all(isinstance(key, str) and isinstance(value, str) for key, value in env.items())
    ):
        logger.warning("Skipping MCP server %r: 'env' must map strings to strings.", name)
        return False

    return True

def print_mcp_servers() -> str:
    mcp_path = get_mcp_path()
    servers = read_mcp_servers(mcp_path)
    valid_server = []

    if not servers:
        return "No available MCP servers."
    else:
        for name, server in servers.items():
            if validate_mcp_server(name, server):
                valid_server.append(name)

    if not valid_server:
        return "No available MCP servers."
    else:
        results = "Available MCP servers:\n"
        results += "\n".join(valid_server)
        return results
