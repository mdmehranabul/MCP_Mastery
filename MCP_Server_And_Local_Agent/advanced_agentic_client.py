import asyncio
from langchain_ollama import ChatOllama
from mcp_use import MCPAgent, MCPClient
import os

async def main():

    client = MCPClient.from_config_file(os.path.join(os.path.dirname(__file__),"mcp-http.json"))
    llm = ChatOllama(base_url="http://localhost:11434",model="qwen3:latest")
    agent = MCPAgent(llm=llm, client=client, max_steps = 30,use_server_manager=True)

    result = await agent.run("What is the current weather in New York and 3 day forecast? Also, what is 12 multiple by 19")
    print(result)

asyncio.run(main())