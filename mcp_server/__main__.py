from mcp_server.server import mcp

if __name__ == "__main__":
    from app.config import settings

    mcp.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
    )
