import os
import logging
import keyword
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
from google.adk.agents import Agent
from google.adk.skills import load_skill_from_dir, Skill
from google.adk.tools.skill_toolset import SkillToolset
from utils.skill_helpers import get_all_skill_names, get_skills_path
from ..mcp_agent.tools import list_mcp_servers

logger = logging.getLogger(__name__)

GOOGLE_MODEL = os.getenv("GOOGLE_MODEL")
model = GOOGLE_MODEL if GOOGLE_MODEL else "gemini-2.5-flash"

@dataclass(frozen=True)
class SkillSubagent:
    skill_name: str
    agent: Agent

def _get_other_skill_names() -> List[str]:
    mcp_servers = list_mcp_servers()
    mcp_names = []
    if mcp_servers != "No available MCP servers.":
        mcp_names = [name for name in mcp_servers.splitlines() if name]

    skill_names = get_all_skill_names()
    if mcp_names:
        other_names = [name for name in skill_names if name not in mcp_names]
    else:
        other_names = skill_names

    return other_names

def _to_agent_name(skill_name: str) -> str:
    agent_name = re.sub(r"\W", "_", skill_name)
    if not agent_name or not agent_name.isidentifier() or keyword.iskeyword(agent_name):
        agent_name = f"skill_{agent_name}"
    return agent_name

def _get_other_skill(path: str | Path, skill_name: str) -> Skill | None:
    skill_path = Path(path) / skill_name
    try:
        skill = load_skill_from_dir(skill_path)
        return skill
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("Skipping skill: %r: %s", skill_name, exc)
        return None

def _create_subagent(skill_name: str) -> Agent | None:
    path = get_skills_path()
    skill = _get_other_skill(path=path, skill_name=skill_name)
    if skill:
        skill_toolset = SkillToolset(skills=[skill])
        skill_agent = Agent(
            model=model,
            name=_to_agent_name(skill_name),
            description=skill.description,
            instruction=skill.instructions,
            tools=[skill_toolset]
        )
        return skill_agent
    else:
        return None

def create_subagent_records() -> List[SkillSubagent] | None:
    skill_names = _get_other_skill_names()

    if not skill_names:
        return None

    subagents: List[SkillSubagent] = []
    for skill_name in skill_names:
        skill_agent = _create_subagent(skill_name)
        if skill_agent:
            subagents.append(SkillSubagent(skill_name=skill_name, agent=skill_agent))

    return subagents
