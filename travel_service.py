from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TravelService")

@mcp.tool()
async def get_tourist_attractions(location: str) -> str:
    """Get top tourist attractions for a location."""
    attractions = {
        "New York": "Statue of Liberty, Central Park, Empire State Building",
        "San Francisco": "Golden Gate Bridge, Alcatraz, Fisherman's Wharf",
        "Seattle": "Space Needle, Pike Place Market, Museum of Pop Culture",
        "London": "Big Ben, Tower of London, British Museum",
        "Paris": "Eiffel Tower, Louvre, Notre-Dame",
        "Tokyo": "Senso-ji Temple, Tokyo Tower, Shibuya Crossing",
    }
    result = attractions.get(location, "No data available")
    return f"Top attractions in {location}: {result}"


@mcp.tool()
async def get_local_food(location: str) -> str:
    """Get local food recommendations for a location."""
    food = {
        "New York": "Pizza, Bagels, Cheesecake",
        "San Francisco": "Sourdough bread, Cioppino, Mission burritos",
        "Seattle": "Salmon, Coffee, Oysters",
        "London": "Fish and chips, Sunday roast, Afternoon tea",
        "Paris": "Croissants, Escargot, Macarons",
        "Tokyo": "Sushi, Ramen, Tempura",
    }
    result = food.get(location, "No data available")
    return f"Must-try food in {location}: {result}"
