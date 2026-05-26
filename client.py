import asyncio
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


load_dotenv()


llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model=os.getenv("CHAT_MODEL"),
    temperature=0
)
server_params = StdioServerParameters(
    command="python3",
    args=["server.py"]
)
async def call_tool(tool_name, args={}):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                tool_name,
                args
            )
            return result
async def choose_tool(query):
    prompt = f"""
    You are an AI GPS Fleet Agent.
    Available tools:
    1. refresh_logs
       - refresh GPS logs
    2. get_all_vehicles
       - get current vehicle status
    3. analyze_fleet
       - analyze suspicious activity
    User query:
    {query}
    RULES:
    - Return ONLY tool name
    - If no tool is needed return "chat"
    Examples:
    "show all vehicles"
    -> get_all_vehicles
    "analyze suspicious vehicles"
    -> analyze_fleet
    "refresh gps logs"
    -> refresh_logs
    "hello"
    -> chat
    """
    response = llm.invoke(prompt)
    return response.content.strip()
async def chat_with_model(user_message: str):
    response = llm.invoke([
        HumanMessage(content=user_message)
    ])
    return response.content
async def agent(query):
    tool_name = await choose_tool(query)
    print(f"\nTOOL CHOSEN: {tool_name}")
    if tool_name == "chat":
        response = await chat_with_model(query)
        print("\nAI RESPONSE:\n")
        print(response)
        return
    result = await call_tool(tool_name)
    print("\nTOOL RESULT:\n")
    print(result)
while True:
    q = input("\nYou: ")
    asyncio.run(agent(q))