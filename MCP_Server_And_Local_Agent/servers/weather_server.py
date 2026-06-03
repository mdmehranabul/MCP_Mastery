import httpx
from fastmcp import FastMCP

mcp = FastMCP("Weather")

@mcp.tool()
async def get_weather(location: str) ->str:
    "Get current weather for a location"
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://wttr.in/{location}?format=j1")
        data = response.json()

        current = data["current_condition"][0]
        area = data["nearest_area"][0]["areaName"][0]["value"]

        return f"Weather in {area}: {current['temp_C']}, {current['weatherDesc'][0]['value']}"
    
@mcp.tool()
async def get_forecast(location: str) ->str:
    """Get 3-day weather forecast"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://wttr.in/{location}?format=j1")
        data = response.json()
        weather_data = data.get("weather")

        if not isinstance(weather_data, list):
            return f"Unexpected weather format for {location}"

        result = f"3-day forecast for {location}:\n"
        for day in weather_data[:3]:
            result +=f"{day['date']}:{day['mintempC']} - {day['maxtempC']} \n"
        return str(result)
    
if __name__ == "__main__":
    # mcp.run(transport="streamable-http")
    # mcp.run(transport="stdio")
    mcp.run(transport="streamable-http", port =8001)