from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import cereal.messaging as messaging
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

# Initialize FastMCP server
mcp = FastMCP("carState")
sm = messaging.SubMaster(['carState', 'modelV2'])

@mcp.tool()
async def get_car_state() -> Any:
    """
    Get the current car state.
    """
    # Wait for the latest carState message
    sm.update(100)

    # Return the latest carState data
    return sm['carState'].to_dict()

@mcp.tool()
async def get_vision_data() -> Any:
    """
    Get the current vision data.
    """
    # Wait for the latest modelV2 message
    sm.update(100)

    # Return the latest modelV2 data
    return sm['modelV2'].to_dict()


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server  # noqa: WPS437

    import argparse

    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)