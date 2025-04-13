"""
Example of using HeterogeneousGroupChat with different agent frameworks.
"""

import os
import asyncio
import openai
from agent_mcp.enhanced_mcp_agent import EnhancedMCPAgent
from agent_mcp.langchain_mcp_adapter import LangchainMCPAdapter
from agent_mcp.heterogeneous_group_chat import HeterogeneousGroupChat
from agent_mcp.mcp_transport import HTTPTransport

# Langchain imports
from langchain_openai import ChatOpenAI
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import Tool
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage

# Check for OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

openai.api_key = api_key

async def setup_langchain_agent():
    """Setup a Langchain agent with search capabilities"""
    # Create Langchain tools
    search = DuckDuckGoSearchAPIWrapper()
    search_tool = Tool(
        name="duckduckgo_search",
        description="Search the web using DuckDuckGo",
        func=search.run
    )
    tools = [search_tool]
    
    # Create Langchain model and agent
    llm = ChatOpenAI(temperature=0)
    agent = OpenAIFunctionsAgent.from_llm_and_tools(
        llm=llm,
        tools=tools,
        system_message=SystemMessage(content=(
            "You are a research assistant that helps find and analyze information."
        ))
    )
    
    # Create the agent executor
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent, agent_executor

async def create_worker_agents(api_key: str):
    """Create a list of worker agents"""
    # Create Autogen worker
    autogen_worker = EnhancedMCPAgent(
        name="AutogenWorker",
        transport=HTTPTransport(host="localhost", port=8001),
        client_mode=True,
        system_message="I help with text analysis and summarization",
        llm_config={
            "config_list": [{
                "model": "gpt-3.5-turbo",
                "api_key": api_key
            }]
        }
    )
    
    # Create Langchain worker
    langchain_agent, agent_executor = await setup_langchain_agent()
    langchain_worker = LangchainMCPAdapter(
        name="LangchainWorker",
        transport=HTTPTransport(host="localhost", port=8002),
        client_mode=True,
        langchain_agent=langchain_agent,
        agent_executor=agent_executor
    )
    
    return [autogen_worker, langchain_worker]

async def main():
    # Create the group chat
    group = HeterogeneousGroupChat(
        name="ResearchTeam",
        host="https://localhost:8000"
    )
    
    # Create and add the coordinator
    coordinator = group.create_coordinator(api_key)
    
    # Create and add all worker agents at once
    workers = await create_worker_agents(api_key)
    group.add_agents(workers)
    
    # Connect all agents
    await group.connect()
    
    # Define a collaborative task
    task = {
        "task_id": "research_task_1",
        "type": "collaborative_task",
        "description": "Research the latest developments in quantum computing and prepare a summary",
        "steps": [
            {
                "agent": "LangchainWorker",
                "task_id": "research_task_1_LangchainWorker",
                "description": "Search for recent quantum computing breakthroughs in 2024",
                "url": "http://localhost:8002"
            },
            {
                "agent": "AutogenWorker",
                "task_id": "research_task_1_AutogenWorker",
                "description": "Analyze and summarize the findings",
                "url": "http://localhost:8001",
                "depends_on": ["research_task_1_LangchainWorker"]
            }
        ]
    }
    
    # Submit task and wait for completion
    await group.submit_task(task)
    await group.wait_for_completion()

if __name__ == "__main__":
    asyncio.run(main())
