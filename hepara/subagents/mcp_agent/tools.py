from typing import List
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool import McpToolset
from .subagents import create_subagent_records

subagent_records = create_subagent_records()
subagents = [record.agent for record in subagent_records] if subagent_records else None

def create_agent_tools() -> List[AgentTool] | None:
    agent_tools: List[AgentTool] = []
    if subagents:
        for subagent in subagents:
            agent_tools.append(AgentTool(subagent))
        return agent_tools
    else:
        return None

def list_mcp_servers():
    if subagent_records is None:
        return "No available MCP servers."

    server_names = ""
    for record in subagent_records:
        server_names += f"{record.server_name}\n"
    return server_names

async def list_mcp_tools(name: str):
    if subagent_records is None:
        return "No available MCP servers."

    valid_names = [record.server_name for record in subagent_records]
    if name not in valid_names:
        return f"{name} is not a valid MCP server."

    mcp_toolsets = []
    for record in subagent_records:
        if record.server_name == name:
            mcp_toolsets = [
                tool for tool in record.agent.tools if isinstance(tool, McpToolset)
            ]
            break

    if not mcp_toolsets:
        return f"No tool for MCP server: {name}."

    tool_names = []
    for toolset in mcp_toolsets:
        try:
            available_tools = await toolset.get_tools()
        except Exception as exc:
            return f"Could not list tools for MCP server {name}: {exc}"
        tool_names.extend(tool.name for tool in available_tools)

    if not tool_names:
        return f"No tool for MCP server: {name}."
    return "\n".join(tool_names) + "\n"
