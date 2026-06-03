from fastmcp import FastMCP

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a*b

@mcp.tool
def subtract(a:int, b:int) -> int:
    """Subtract two numbers"""
    return a - b

@mcp.tool
def divide(a:int, b:int) -> float:
    if b == 0:
        return "Error: Division by 0 "
    return a/b

if __name__ == "__main__":
    # mcp.run(transport="stdio")
    mcp.run(transport="streamable-http",port = 8000)