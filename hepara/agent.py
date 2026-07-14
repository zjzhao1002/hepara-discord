import os
from google.adk.agents.llm_agent import Agent
from google.adk.tools.agent_tool import AgentTool
from .subagents.inspirehep_agent.agent import inspirehep_agent
from .subagents.arxiv_agent.agent import arxiv_agent
from .subagents.faq_agent.agent import faq_agent
from .subagents.pdg_agent.agent import pdg_agent
from .subagents.mcp_agent.agent import mcp_agent
from .subagents.skills_agent.agent import skills_agent
from .prompt import HEP_COORDINATOR_PROMPT


GOOGLE_MODEL = os.getenv("GOOGLE_MODEL") 
model = GOOGLE_MODEL if GOOGLE_MODEL else "gemini-2.5-flash"

coordinator_tools = [
    AgentTool(inspirehep_agent),
    AgentTool(arxiv_agent),
    AgentTool(faq_agent),
    AgentTool(pdg_agent),
]
if mcp_agent is not None:
    coordinator_tools.append(AgentTool(mcp_agent))
if skills_agent is not None:
    coordinator_tools.append(AgentTool(skills_agent))

hep_coordinator = Agent(
    model=model,
    name='hep_coordinator',
    description="""
        You are a research assistant in High Energy Physics, 
        tracking citations of user, locating current papers, 
        and answer relevant questions.
    """,
    instruction=HEP_COORDINATOR_PROMPT,
    tools=coordinator_tools, # type: ignore
)
