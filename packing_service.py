from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PackingService")

@mcp.tool()
async def suggest_packing_items(weather_description: str) -> str:
    """Suggest items to pack based on the weather description."""
    packing_suggestions = []
    
    weather_lower = weather_description.lower()
    
    if "sunny" in weather_lower:
        packing_suggestions.extend(["sunglasses", "sunscreen", "hat", "light clothing"])
    
    if "rainy" in weather_lower or "rain" in weather_lower:
        packing_suggestions.extend(["umbrella", "raincoat", "waterproof boots"])
    
    if "cloudy" in weather_lower or "foggy" in weather_lower:
        packing_suggestions.extend(["light jacket", "layers"])
    
    if "cold" in weather_lower or any(temp in weather_lower for temp in ["10°C", "12°C", "15°C"]):
        packing_suggestions.extend(["warm jacket", "scarf", "gloves"])
    
    if not packing_suggestions:
        packing_suggestions = ["appropriate clothing for the weather"]
    
    return f"Based on the weather ({weather_description}), you should pack: {', '.join(packing_suggestions)}"
