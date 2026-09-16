import json
import os
import sqlite3
from pathlib import Path

from mcp.server import MCPServer


# Create the MCP server
mcp = MCPServer("Real Estate Server")


# ---------------------------------------------------------
# DATABASE LOCATION
# ---------------------------------------------------------
#
# Defaults to a "database/properties.db" folder next to this file,
# which is portable across machines/OSes. Set REAL_ESTATE_DB_PATH in
# your .env if you keep properties.db somewhere else.

DB_PATH = Path(os.getenv(
    "REAL_ESTATE_DB_PATH",
    str(Path(__file__).resolve().parent / "database" / "properties.db"),
))


# ---------------------------------------------------------
# TOOL 1: Get complete property inventory
# ---------------------------------------------------------

@mcp.tool()
def get_property_inventory() -> str:
    """Get all available properties from the real estate inventory."""

    connection = sqlite3.connect(DB_PATH)
    # we are making the connection between python and sql
    connection.row_factory = sqlite3.Row
    # this helps to access the rows in the database by column names too

    cursor = connection.cursor()
    # cursor helps to execute the sql query

    cursor.execute("""
        SELECT *
        FROM properties
        WHERE LOWER(availability) LIKE 'available%'
    """)
    # The % means anything can come after available.

    rows = cursor.fetchall()
    # fetchall() : means give me all the rows of the result of this query

    connection.close()

    properties = [dict(row) for row in rows]

    return json.dumps(properties, indent=2)


# ---------------------------------------------------------
# TOOL 2: Search properties using optional filters
# ---------------------------------------------------------

@mcp.tool()
def search_properties(
    city: str = "",
    location: str = "",
    property_type: str = "",
    bhk: int = 0,
    max_price: int = 0,
    min_area: int = 0,
    parking: bool = False,
    furnished: str = "",
    max_metro_distance: float = 0
) -> str:
    """Search available properties using optional filters."""

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    query = """
        SELECT *
        FROM properties
        WHERE LOWER(availability) LIKE 'available%'
    """

    parameters = []

    # City filter
    if city:
        query += " AND LOWER(city) = LOWER(?)"
        parameters.append(city)

    # Location / sector filter
    if location:
        query += " AND LOWER(location) LIKE LOWER(?)"
        parameters.append(f"%{location}%")

    # Property type filter
    if property_type:
        query += " AND LOWER(property_type) = LOWER(?)"
        parameters.append(property_type)

    # BHK filter
    if bhk > 0:
        query += " AND bhk = ?"
        parameters.append(bhk)

    # Maximum price filter
    if max_price > 0:
        query += " AND price <= ?"
        parameters.append(max_price)

    # Minimum area filter
    if min_area > 0:
        query += " AND area_sqft >= ?"
        parameters.append(min_area)

    # Parking filter
    if parking:
        query += " AND LOWER(parking) = 1"

    # Furnishing filter
    if furnished:
        query += " AND LOWER(furnished) LIKE LOWER(?)"
        parameters.append(f"%{furnished}%")

    # Maximum metro distance
    if max_metro_distance > 0:
        query += " AND metro_distance_km <= ?"
        parameters.append(max_metro_distance)

    # Execute the final query
    cursor.execute(query, parameters)

    rows = cursor.fetchall()

    connection.close()

    properties = [dict(row) for row in rows]

    return json.dumps(properties, indent=2)


# ---------------------------------------------------------
# TOOL 3: Get property details
# ---------------------------------------------------------

@mcp.tool()
def get_property_details(property_id: str) -> str:
    """Get complete details for a specific property."""

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM properties
        WHERE property_id = ?
        AND LOWER(availability) LIKE 'available%'
        """,
        (property_id,)
    )

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return json.dumps({
            "success": False,
            "message": "Property not found."
        })

    property_details = dict(row)

    return json.dumps(property_details, indent=2)


# ---------------------------------------------------------
# TOOL 4: Get properties by location
# ---------------------------------------------------------

@mcp.tool()
def get_properties_by_location(
    city: str,
    location: str = ""
) -> str:
    """Get available properties in a specific city or location."""

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    query = """
        SELECT *
        FROM properties
        WHERE LOWER(availability) LIKE 'available%'
        AND LOWER(city) = LOWER(?)
    """

    parameters = [city]

    if location:
        query += " AND LOWER(location) LIKE LOWER(?)"
        parameters.append(f"%{location}%")

    cursor.execute(query, parameters)

    rows = cursor.fetchall()

    connection.close()

    properties = [dict(row) for row in rows]

    return json.dumps(properties, indent=2)


# ---------------------------------------------------------
# Run MCP server
# ---------------------------------------------------------

if __name__ == "__main__":
    mcp.run()