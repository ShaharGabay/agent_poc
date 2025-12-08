from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WeatherService")

@mcp.tool()
async def get_weather(location: str) -> str:
    """Get current weather for a location."""
    weather_data = {
        "New York": "sunny, 25C",
        "San Francisco": "foggy, 18C",
        "Seattle": "rainy, 15C",
        "London": "cloudy, 12C",
        "Paris": "sunny, 22C",
        "Tokyo": "partly cloudy, 20C",
    }
    weather = weather_data.get(location, "unknown")
    return f"{location}: {weather}"
