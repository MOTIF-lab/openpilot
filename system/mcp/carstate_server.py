from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import cereal.messaging as messaging

# Initialize FastMCP server
mcp = FastMCP("carState")
sm = messaging.SubMaster(['carState'])

@mcp.tool()
async def get_car_state() -> Any:
    """
    Get the current car state.
    """
    # Wait for the latest carState message
    sm.update(0)

    # Return the latest carState data
    return sm['carState'].to_dict()

if __name__ == "__main__":
    # Start the FastMCP server
    mcp.run(transport='stdio')