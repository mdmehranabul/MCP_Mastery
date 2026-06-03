import asyncio
from langchain_ollama import ChatOllama
from mcp_use import MCPAgent, MCPClient

async def main():
    config = {
        "mcpServers": {
            "weather":{
                "command":"uv",
                "args":["run",
                        "--directory",
                        "/Users/mdmehranabul/Desktop/Learning/MCP_Mastery/MCP_Server_And_Local_Agent",
                        "weather_server.py"]

            }
            
        }
    }

    client = MCPClient.from_dict(config)
    llm = ChatOllama(base_url="http://localhost:11434",model="gpt-oss:latest")
    agent = MCPAgent(llm=llm, client=client)

    result = await agent.run("What is the current weather in New York and 3 day forecast?")
    print(result)

asyncio.run(main())