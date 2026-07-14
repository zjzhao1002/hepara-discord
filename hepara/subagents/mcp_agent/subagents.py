import os
import logging
import keyword
import re
from dataclasses import dataclass
from typing import Any, List
from pathlib import Path
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.skills import load_skill_from_dir, Skill
from google.adk.tools.skill_toolset import SkillToolset
from mcp import StdioServerParameters
from utils.mcp_helpers import get_mcp_path, read_mcp_servers, validate_mcp_server

logger = logging.getLogger(__name__)

SKILL_PATH = os.getenv("SKILL_PATH")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL")
model = GOOGLE_MODEL if GOOGLE_MODEL else "gemini-2.5-flash"

@dataclass(frozen=True)
class McpSubagent:
    server_name: str
    agent: Agent

def _create_mcp_toolset(name: str, server: Any) -> McpToolset | None:
    if not validate_mcp_server(name, server):
        return None

    command = server["command"]
    args = server.get("args", [])
    env = server.get("env")

    try:
        return McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=command,
                    args=args,
                    env=env,
                ),
                timeout=10
            )
        )
    except (TypeError, ValueError) as exc:
        logger.warning("Skipping MCP server %r: %s", name, exc)
        return None

def _get_mcp_skill(path: str | Path, skill_name: str) -> Skill | None:
    skill_path = Path(path) / skill_name
    try:
        skill = load_skill_from_dir(skill_path)
        return skill
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("Skipping skill: %r: %s", skill_name, exc)
        return None

def _to_agent_name(name: str) -> str:
    agent_name = re.sub(r"\W", "_", name)
    if not agent_name or not agent_name.isidentifier() or keyword.iskeyword(agent_name):
        agent_name = f"mcp_{agent_name}"
    return agent_name

def _create_subagent(name: str, mcp_toolset: McpToolset, skill: Skill | None) -> Agent:
    agent_name = _to_agent_name(name)
    if skill is not None:
        skill_toolset = SkillToolset(skills=[skill])
        subagent = Agent(
            model = model,
            name = agent_name,
            description=skill.description,
            instruction=skill.instructions,
            tools = [mcp_toolset, skill_toolset]
        )
        return subagent
    else:
        subagent = Agent(
            model=model,
            name=agent_name,
            description=f"A subagent to use {name} MCP server to response user request.",
            instruction=f"You task is to use tools from {name} MCP server to response user request.",
            tools=[mcp_toolset]
        )
        return subagent

def create_subagent_records() -> List[McpSubagent] | None:
    path = get_mcp_path()
    servers = read_mcp_servers(path)
    if not servers:
        return None

    subagents: List[McpSubagent] = []
    for name, server in servers.items():
        toolset = _create_mcp_toolset(name, server)
        if toolset is None:
            continue
        if SKILL_PATH:
            skill = _get_mcp_skill(SKILL_PATH, name)
            subagent = _create_subagent(name, toolset, skill)
        else:
            subagent = _create_subagent(name, toolset, None)
        subagents.append(McpSubagent(server_name=name, agent=subagent))

    return subagents
