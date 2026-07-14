import os
from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool
from .prompt import PDG_AGENT_PROMPT
from .tools import get_particle_masses, get_particle_widths, get_particle_lifetime, get_particle_decays

get_particle_masses_tool = FunctionTool(func=get_particle_masses)
get_particle_widths_tool = FunctionTool(func=get_particle_widths)
get_particle_lifetime_tool = FunctionTool(func=get_particle_lifetime)
get_particle_decays_tool = FunctionTool(func=get_particle_decays)

GOOGLE_MODEL = os.getenv("GOOGLE_MODEL") 
model = GOOGLE_MODEL if GOOGLE_MODEL else "gemini-2.5-flash"

pdg_agent = Agent(
    model=model,
    name='pdg_agent',
    description='A helpful assistant to retrieve data from PDG.',
    instruction=PDG_AGENT_PROMPT,
    tools=[get_particle_masses_tool, get_particle_widths_tool, get_particle_lifetime_tool, get_particle_decays_tool],
    output_key="pdg_report"
)