import streamlit as st
import asyncio
from langchain_ollama import ChatOllama

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

from langchain.agents import create_agent


server_params = StdioServerParameters(
    command="uv",
    args=["--directory",
          "/Users/mdmehranabul/Desktop/Learning/MCP_Mastery/MCP_RAG_with_Langchain",
          "run",
          "server.py"]
)

st.title(":brain Streamlit App for MCP RAG with Ollama MCP")
st.title("LEARN LLM")

model = ChatOllama(model = "qwen3", base_url="http://localhost:11434/")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] =[]

with st.form("llm-form"):
    text = st.text_area("Enter your question here")
    submit = st.form_submit_button("Submit")
    new_chat = st.form_submit_button("New Chat")
    debug_info = st.checkbox("Show Debug Info")


async def generate_response_async(user_message):
    """Async function to generate response using MCP tools"""
    async with stdio_client(server_params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()

            tools = await load_mcp_tools(session)

            agent = create_agent(model,tools)
            agent_response = await agent.ainvoke({"messages":[{"role":"user","content":user_message}]})

            if debug_info:
                st.write('### Debug - Agent Response')
                st.write(agent_response)
            response = agent_response.get('messages')[-1].content
            return response

def generate_response(user_message):
    """Synchronous wrapper for the async function"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(generate_response_async(user_message))

if submit and text:
    with st.spinner("Generating response..."):
        try:
            response = generate_response(text)
            st.session_state["chat_history"].append({'user':text, 'assistant':response})
            st.success("Response successfully generated")
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")

if new_chat:
    st.session_state['chat_history']=[]
    st.success("Chat history cleared")

if st.session_state['chat_history']:
    st.write('## Chat History')
    for chat in reversed(st.session_state['chat_history']):
        st.write(f"**:adult: User**: {chat['user']}")
        st.write(f"**:brain: Assistant**: {chat['assistant']}")
        st.write("---")