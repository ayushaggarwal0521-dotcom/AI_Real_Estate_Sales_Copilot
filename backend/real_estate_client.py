import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ---------------------------------------------------------
# MCP SERVER LOCATION
# ---------------------------------------------------------
#
# Defaults to "server.py" living next to this file, which is portable
# across machines/OSes. Set REAL_ESTATE_MCP_SERVER_PATH in your .env
# if you keep server.py somewhere else.

SERVER_PATH = os.getenv(
    "REAL_ESTATE_MCP_SERVER_PATH",
    str(Path(__file__).resolve().parent / "server.py"),
)


# ---------------------------------------------------------
# GENERIC MCP TOOL CALLER
# ---------------------------------------------------------

async def call_mcp_tool(tool_name: str, arguments: dict = None):

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_PATH]
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            # Initialize connection with MCP server
            await session.initialize()

            # Call the requested MCP tool
            result = await session.call_tool(
                tool_name,
                arguments=arguments or {}
            )

            # MCP returns content as a text block.
            # Our MCP server returns JSON text,
            # so convert it into normal Python data.
            text = result.content[0].text

            return json.loads(text)


# ---------------------------------------------------------
# BACKEND FUNCTION 1
# GET ALL AVAILABLE PROPERTIES
# ---------------------------------------------------------

def get_all_properties():

    result = asyncio.run(
        call_mcp_tool(
            "get_property_inventory"
        )
    )

    return result


# ---------------------------------------------------------
# BACKEND FUNCTION 2
# SEARCH PROPERTIES
# ---------------------------------------------------------

def search_properties(
    city="",
    location="",
    property_type="",
    bhk=0,
    max_price=0,
    min_area=0,
    parking=False,
    furnished="",
    max_metro_distance=0
):

    result = asyncio.run(
        call_mcp_tool(
            "search_properties",
            {
                "city": city,
                "location": location,
                "property_type": property_type,
                "bhk": bhk,
                "max_price": max_price,
                "min_area": min_area,
                "parking": parking,
                "furnished": furnished,
                "max_metro_distance": max_metro_distance
            }
        )
    )

    return result


# ---------------------------------------------------------
# BACKEND FUNCTION 3
# GET PROPERTIES BY LOCATION
# ---------------------------------------------------------

def get_properties_by_location(
    city,
    location=""
):

    result = asyncio.run(
        call_mcp_tool(
            "get_properties_by_location",
            {
                "city": city,
                "location": location
            }
        )
    )

    return result


# ---------------------------------------------------------
# BACKEND FUNCTION 4
# GET PROPERTY DETAILS
# ---------------------------------------------------------

def get_property_details(property_id):

    result = asyncio.run(
        call_mcp_tool(
            "get_property_details",
            {
                "property_id": property_id
            }
        )
    )

    return result


# ---------------------------------------------------------
# TEST THE BACKEND
# ---------------------------------------------------------

if __name__ == "__main__":

    print("\n==============================")
    print("TEST: PROPERTY DETAILS")
    print("==============================")

    property_details = get_property_details(
        property_id="PROP-1011"
    )

    print("Property details:\n")
    print(property_details)