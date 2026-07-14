import os
from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool
from .prompt import INSPIREHEP_AGENT_PROMPT
from .tools import get_author_citations, get_paper_citations, track_citations_updates, search_papers

GOOGLE_MODEL = os.getenv("GOOGLE_MODEL") 
model = GOOGLE_MODEL if GOOGLE_MODEL else "gemini-2.5-flash"

get_author_citations_tool = FunctionTool(func=get_author_citations)
get_paper_citations_tool = FunctionTool(func=get_paper_citations)
track_citations_updates_tool = FunctionTool(func=track_citations_updates)
search_papers_tool = FunctionTool(func=search_papers)

inspirehep_agent = Agent(
    model=model,
    name='inspirehep_agent',
    description='A helpful assistant for tracking paper citations of the user and retrieving citation graphs (references or citations) for specific papers.',
    instruction=INSPIREHEP_AGENT_PROMPT,
    tools=[get_author_citations_tool, get_paper_citations_tool, track_citations_updates_tool, search_papers_tool],
    output_key="inspirehep_report"
)
