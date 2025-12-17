from agent.mcp_persistence import mcp

print("Inspecting FastMCP tools parameters...")
for name, tool in mcp._tool_manager._tools.items():
    print(f"Tool: {name}")
    print(f"Parameters Type: {type(tool.parameters)}")
    print(f"Parameters: {tool.parameters}")
