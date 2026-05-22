from mcp.server.fastmcp import FastMCP

from src.tools import check_coverage, get_requirement, list_categories, search_requirements

mcp = FastMCP("owasp-rag", host="0.0.0.0", port=8080)
mcp.tool()(search_requirements)
mcp.tool()(get_requirement)
mcp.tool()(list_categories)
mcp.tool()(check_coverage)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
