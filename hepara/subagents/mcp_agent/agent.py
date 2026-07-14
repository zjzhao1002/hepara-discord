import os
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from .tools import list_mcp_servers, create_agent_tools, list_mcp_tools
from .prompt import MCP_AGENT_PROMPT

GOOGLE_MODEL = os.getenv("GOOGLE_MODEL")
model = GOOGLE_MODEL if GOOGLE_MODEL else "gemini-2.5-flash"

list_mcp_servers_tool = FunctionTool(func=list_mcp_servers)
list_mcp_tools_tool = FunctionTool(func=list_mcp_tools)
all_tools = [list_mcp_servers_tool, list_mcp_tools_tool]
agent_tools = create_agent_tools()
if agent_tools:
    all_tools += agent_tools

mcp_agent = Agent(
    model=model,
    name="mcp_agent",
    description="A MCP manager to call tools from external MCP servers.",
    tools=all_tools, # type: ignore
    instruction=MCP_AGENT_PROMPT
) if agent_tools else None
