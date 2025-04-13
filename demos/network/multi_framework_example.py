"""
Example of using multiple agent frameworks together in a collaborative task.

This example demonstrates how agents from Autogen, Langchain, CrewAI, and LangGraph
can work together seamlessly through the MCP framework.
"""

import os
import asyncio
import openai
from crewai import Agent as CrewAgent
from langchain.tools import Tool
from agent_mcp.enhanced_mcp_agent import EnhancedMCPAgent
from agent_mcp.langchain_mcp_adapter import LangchainMCPAdapter
from agent_mcp.crewai_mcp_adapter import CrewAIMCPAdapter
from agent_mcp.langgraph_mcp_adapter import LangGraphMCPAdapter
from agent_mcp.heterogeneous_group_chat import HeterogeneousGroupChat
from agent_mcp.mcp_transport import HTTPTransport

# Standard imports for Langchain
from langchain_openai import ChatOpenAI
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage

# Check for OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

openai.api_key = api_key

async def setup_langchain_agent():
    """Setup a Langchain agent with search capabilities"""
    search = DuckDuckGoSearchAPIWrapper()
    search_tool = Tool(
        name="duckduckgo_search",
        description="Search the web using DuckDuckGo",
        func=search.run
    )
    tools = [search_tool]
    
    llm = ChatOpenAI(temperature=0)
    agent = OpenAIFunctionsAgent.from_llm_and_tools(
        llm=llm,
        tools=tools,
        system_message=SystemMessage(content=(
            "You are a research assistant that helps find information."
        ))
    )
    
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent, agent_executor

def setup_crewai_agent():
    """Setup a CrewAI agent for analysis"""
    return CrewAgent(
        role="Data Analyst",
        goal="Analyze and extract insights from research data",
        backstory="You are an expert data analyst with experience in scientific research",
        allow_delegation=False
    )

def setup_summary_tools():
    """Setup tools for summarization"""
    llm = ChatOpenAI(temperature=0)
    
    # Create a summarization tool
    async def summarize(input: str) -> str:
        """Summarize text in a clear and concise way"""
        response = await llm.ainvoke(
            "Summarize the following in a clear and concise way: " + input
        )
        return response.content
        
    summarize_tool = Tool(
        name="summarize",
        description="Summarize text in a clear and concise way",
        func=summarize
    )
    
    return [summarize_tool]

async def create_worker_agents():
    """Create agents from different frameworks"""
    # Autogen worker for task coordination
    autogen_worker = EnhancedMCPAgent(
        name="AutogenWorker",
        transport=HTTPTransport(host="localhost", port=8001),
        client_mode=True,
        system_message="I help coordinate tasks and integrate results",
        llm_config={
            "config_list": [{
                "model": "gpt-3.5-turbo",
                "api_key": api_key
            }]
        }
    )
    
    # Langchain worker for research
    langchain_agent, agent_executor = await setup_langchain_agent()
    langchain_worker = LangchainMCPAdapter(
        name="LangchainWorker",
        transport=HTTPTransport(host="localhost", port=8002),
        client_mode=True,
        langchain_agent=langchain_agent,
        agent_executor=agent_executor
    )
    
    # CrewAI worker for analysis
    crewai_agent = setup_crewai_agent()
    crewai_worker = CrewAIMCPAdapter(
        name="CrewAIWorker",
        transport=HTTPTransport(host="localhost", port=8003),
        client_mode=True,
        crewai_agent=crewai_agent
    )
    
    # LangGraph worker for summarization
    summary_tools = setup_summary_tools()
    langgraph_worker = LangGraphMCPAdapter(
        name="LangGraphWorker",
        transport=HTTPTransport(host="localhost", port=8004),
        client_mode=True,
        tools=summary_tools
    )
    
    return [
        autogen_worker,
        langchain_worker,
        crewai_worker,
        langgraph_worker
    ]

async def main():
    # Create the group chat
    group = HeterogeneousGroupChat(
        name="ResearchTeam",
        server_url="https://mcp-server-ixlfhxquwq-ew.a.run.app"
    )
    
    # Create and add the coordinator
    coordinator = group.create_coordinator(api_key)
    
    # Create and add all worker agents
    workers = await create_worker_agents()
    group.add_agents(workers)
    
    # Connect all agents
    await group.connect()
    
    # Define a collaborative research task
    task = {
        "task_id": "quantum_research",
        "type": "collaborative_task",
        "description": "Research and analyze quantum computing developments",
        "steps": [
            {
                "agent": "LangchainWorker",
                "task_id": "research",
                "description": "Search for recent quantum computing breakthroughs in 2024",
                "url": "https://mcp-server-ixlfhxquwq-ew.a.run.app"
            },
            {
                "agent": "CrewAIWorker",
                "task_id": "analysis",
                "description": "Analyze the research findings and identify key trends and implications",
                "url": "https://mcp-server-ixlfhxquwq-ew.a.run.app",
                "depends_on": ["research"]
            },
            {
                "agent": "AutogenWorker",
                "task_id": "integration",
                "description": "Integrate the research and analysis into a cohesive narrative",
                "url": "https://mcp-server-ixlfhxquwq-ew.a.run.app",
                "depends_on": ["analysis"]
            },
            {
                "agent": "LangGraphWorker",
                "task_id": "summary",
                "description": "Create a final executive summary of all findings",
                "url": "https://mcp-server-ixlfhxquwq-ew.a.run.app",
                "depends_on": ["integration"]
            }
        ]
    }
    
    # Submit task and wait for completion
    await group.submit_task(task)
    await group.wait_for_completion()

if __name__ == "__main__":
    asyncio.run(main())
