"""
Test script for heterogeneous agents working together through the deployed server.
"""

import os
import asyncio
from enhanced_mcp_agent import EnhancedMCPAgent
from langchain_mcp_adapter import LangchainMCPAdapter
from heterogeneous_group_chat import HeterogeneousGroupChat
import json

# Langchain imports
from langchain_openai import ChatOpenAI
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import Tool
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage

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

async def main():
    #the idea here is agent in a group working with each other regardless of the framework they were built on
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable")
    
    # Create a group chat
    group = HeterogeneousGroupChat(
        name="TechResearch",
        server_url="https://mcp-server-ixlfhxquwq-ew.a.run.app"
    )
    
    print("\n=== Creating Coordinator ===")
    # Create and initialize coordinator
    coordinator = group.create_coordinator(api_key=api_key)
    print(f"Coordinator created with name: {coordinator.name}")
    
    # Verify coordinator transport
    if not coordinator.transport:
        raise ValueError("Coordinator transport not initialized")
    print(f"Coordinator transport initialized with URL: {coordinator.transport.get_url()}")
    
    print("\n=== Creating Agents ===")
    # Create an Autogen-based researcher
    researcher = EnhancedMCPAgent(
        name="Researcher",
        system_message="""You are a technology researcher specializing in AI and quantum computing.
        Your role is to analyze topics and provide detailed, technical insights.""",
        llm_config={
            "config_list": [{
                "model": "gpt-3.5-turbo",
                "api_key": api_key
            }]
        }
    )
    
    # Create a Langchain-based analyst with search capabilities
    print("Setting up Langchain agent...")
    langchain_agent, agent_executor = await setup_langchain_agent()
    analyst = LangchainMCPAdapter(
        name="Analyst",
        langchain_agent=langchain_agent,
        agent_executor=agent_executor,
        system_message="""I am a market research analyst specializing in technology trends.
        I use web search to find current market data and analyze industry developments."""
    )
    
    # Add both agents to the group
    print("Adding agents to group...")
    group.add_agents([researcher, analyst])
    
    # Connect everyone to the deployed server
    print("\n=== Connecting to Deployed Server ===")
    try:
        await group.connect()
        print("Successfully connected to server")
        
        # Verify all agents are connected
        for agent in group.agents:
            if not agent.transport or not agent.transport.token:
                raise ValueError(f"Agent {agent.name} not properly connected")
            print(f"Agent {agent.name} connected with token: {agent.transport.token[:8]}...")
            
        # Verify coordinator connection
        if not group.coordinator or not group.coordinator.transport.token:
            raise ValueError("Coordinator not properly connected")
        print(f"Coordinator connected with token: {group.coordinator.transport.token[:8]}...")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        raise
    
    # Define a collaborative task
    task = {
        "task_id": "quantum_ml_research",
        "steps": [
            {
                "task_id": "initial_research",
                "agent": "Researcher",
                "description": """Research the intersection of quantum computing and machine learning.
                Focus on: 
                1. Recent breakthroughs in quantum ML algorithms
                2. Potential applications in real-world scenarios
                3. Current limitations and challenges"""
            },
            {
                "task_id": "market_analysis",
                "agent": "Analyst",
                "description": """Using the research findings, analyze:
                1. Current market adoption of quantum ML
                2. Major companies and research institutions involved
                3. Future market potential and timeline
                Use your search capabilities to find supporting data.""",
                "depends_on": ["initial_research"]
            }
        ]
    }
    
    # Submit the task and wait for completion
    print("\n=== Submitting Task ===")
    print("***** REACHED POINT BEFORE group.submit_task *****", flush=True)
    
    # Verify task structure before submission
    print(f"Task structure: {json.dumps(task, indent=2)}")
    print(f"Active agents: {[agent.name for agent in group.agents]}")
    
    try:
        await group.submit_task(task)
        print("Task submitted successfully")
    except Exception as e:
        print(f"Error submitting task: {e}")
        raise
    
    print("\n=== Waiting for Results ===")
    await group.wait_for_completion()
    
    print("\n=== Task Complete ===\n")
    print("Shutting down agents...")
    await group.shutdown()
    print("All agents shut down successfully")

if __name__ == "__main__":
    asyncio.run(main())
