from mcp.server.fastmcp import FastMCP

mcp = FastMCP("WeatherService")

@mcp.tool()
async def get_weather(location: str) -> str:
    """Get weather for a specified location."""
    # Simulate fetching weather data
    weather_data = {
        "New York": "sunny with a temperature of 25°C",
        "San Francisco": "foggy with a temperature of 18°C",
        "Seattle": "rainy with a temperature of 15°C",
        "London": "cloudy with a temperature of 12°C",
        "Paris": "sunny with a temperature of 22°C",
        "Tokyo": "partly cloudy with a temperature of 20°C",
    }
    weather = weather_data.get(location, "unknown - check local forecast")
    return f"The weather in {location} is {weather}."
