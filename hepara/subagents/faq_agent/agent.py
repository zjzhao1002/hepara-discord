import os
from google.adk.agents.llm_agent import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.google_search_agent_tool import (
    GoogleSearchAgentTool,
    create_google_search_agent,
)
from .prompt import FAQ_AGENT_PROMPT
from .tools import query_chromadb

GOOGLE_MODEL = os.getenv("GOOGLE_MODEL") 
model = GOOGLE_MODEL if GOOGLE_MODEL else "gemini-2.5-flash"

query_chromadb_tool = FunctionTool(func=query_chromadb)
google_search_agent_tool = GoogleSearchAgentTool(create_google_search_agent(model))

faq_agent = Agent(
    model=model,
    name="faq_agent",
    description="A helpful assistant to provide accurate and concise answers to questions based on documents or google search.",
    instruction=FAQ_AGENT_PROMPT,
    tools=[query_chromadb_tool, google_search_agent_tool],
    output_key="faq_report"
)
