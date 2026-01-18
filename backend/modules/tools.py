import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import sys

# Configuration for the MCP Server (SQLite)
# We assume 'mcp-server-sqlite' is installed in the same bin directory as the python interpreter
MCP_SERVER_PARAMS = StdioServerParameters(
    command=os.path.join(os.path.dirname(sys.executable), "mcp-server-sqlite"),
    args=["--db-path", os.path.abspath(os.path.join(os.path.dirname(__file__), "../insurance.db"))],
    env=None
)

async def fetch_rules_mcp(claim_type: str) -> dict:
    """
    Connects to the SQLite MCP server and queries for validation rules based on claim_type.
    """
    async with stdio_client(MCP_SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            # We want to use the 'read_query' tool provided by mcp-server-sqlite
            # Query: SELECT * FROM claim_rules WHERE claim_type = ?
            query = f"SELECT * FROM claim_rules WHERE claim_type = '{claim_type}'"
            
            # Call the tool 'read_query'
            # Note: The exact tool name depends on mcp-server-sqlite implementation.
            # Usually it exposes 'read_query' or similar.
            result = await session.call_tool("read_query", arguments={"query": query})
            
            # Parse result
            if result.content and len(result.content) > 0:
                 raw_text = result.content[0].text
                 print(f"DEBUG: Unknown JSON format. Raw text: {raw_text}")
                 
                 try:
                     # Try standard JSON
                     data = json.loads(raw_text)
                 except json.JSONDecodeError:
                     import ast
                     try:
                         # Fallback for Python-style string representation (single quotes)
                         data = ast.literal_eval(raw_text)
                     except Exception as e:
                        print(f"Failed to parse via ast: {e}")
                        raise
                 
                 if data and isinstance(data, list) and len(data) > 0:
                     return data[0] # Return the first matching rule
            
            return {}

def get_validation_rules(claim_type: str) -> dict:
    """
    Synchronous wrapper for fetch_rules_mcp to be used by ADK.
    """
    try:
        return asyncio.run(fetch_rules_mcp(claim_type))
    except Exception as e:
        import traceback
        error_msg = f"Error fetching rules: {e}\\n{traceback.format_exc()}"
        print(error_msg)
        return {"error": str(e)}
