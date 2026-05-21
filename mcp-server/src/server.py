from mcp.server.fastmcp import FastMCP

mcp = FastMCP("owasp-rag")

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
