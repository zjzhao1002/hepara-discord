import os
from google.adk import Agent
from google.adk.tools import FunctionTool
from .tools import create_agent_tools, has_available_skills, list_all_skills
from .prompt import SKILL_AGENT_PROMPT

GOOGLE_MODEL = os.getenv("GOOGLE_MODEL")
model = GOOGLE_MODEL if GOOGLE_MODEL else "gemini-2.5-flash"

list_all_skills_tool = FunctionTool(func=list_all_skills)
all_tools = [list_all_skills_tool]
agent_tools = create_agent_tools()
if agent_tools:
    all_tools += agent_tools

skills_agent = Agent(
    model=model,
    name="skills_agent",
    description="A Skills manager to use customized skills.",
    instruction=SKILL_AGENT_PROMPT,
    tools=all_tools # type: ignore
) if has_available_skills() else None
