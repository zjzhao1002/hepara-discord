from typing import List
from google.adk.tools import AgentTool
from utils.skill_helpers import get_all_skill_names
from .subagents import create_subagent_records

subagent_records = create_subagent_records()
subagents = [record.agent for record in subagent_records] if subagent_records else None

def has_available_skills() -> bool:
    return bool(get_all_skill_names())

def create_agent_tools() -> List[AgentTool] | None:
    agent_tools: List[AgentTool] = []
    if subagents:
        for subagent in subagents:
            agent_tools.append(AgentTool(subagent))
        return agent_tools
    else:
        return None

def list_all_skills():
    skill_names = get_all_skill_names()
    if not skill_names:
        return "No available skills."

    return "\n".join(skill_names) + "\n"
