"""
Example of heterogeneous agent network with Autogen and Langchain agents.
"""

import os
import asyncio
from typing import Dict, Any
import openai
from agent_mcp.enhanced_mcp_agent import EnhancedMCPAgent
from agent_mcp.langchain_mcp_adapter import LangchainMCPAdapter
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

async def check_task_completion(coordinator, task):
    """Check if all tasks are completed and generate final summary"""
    all_completed = True
    all_results = {}
    
    for step in task["steps"]:
        task_id = step["task_id"]
        if task_id not in coordinator.task_results or coordinator.task_results[task_id] is None:
            all_completed = False
            break
        all_results[task_id] = coordinator.task_results[task_id]
    
    if all_completed:
        print("\n=== All tasks completed! ===")
        print("\nTask Results:")
        for task_id, result in all_results.items():
            print(f"\n{task_id}:")
            print(result)
        
        # Generate final summary using the coordinator
        summary_task = {
            "task_id": "final_summary",
            "description": "Create a comprehensive summary of the quantum computing research. First summarize the initial research findings, then analyze the key insights and implications for the future of quantum computing.",
            "previous_results": all_results,
            "reply_to": "http://localhost:8000"
        }
        
        await coordinator.assign_task("http://localhost:8001", summary_task)
        return True
        
    return False

async def main():
    # Create transport layers
    coordinator_transport = HTTPTransport(host="localhost", port=8000)
    autogen_transport = HTTPTransport(host="localhost", port=8001)
    langchain_transport = HTTPTransport(host="localhost", port=8002)
    
    # Create coordinator agent (Autogen-based)
    coordinator = EnhancedMCPAgent(
        name="Coordinator",
        transport=coordinator_transport,
        server_mode=True,
        system_message="You coordinate tasks between different agents",
        llm_config={
            "config_list": [{
                "model": "gpt-3.5-turbo",
                "api_key": api_key
            }]
        }
    )
    
    # Create Autogen worker agent
    autogen_worker = EnhancedMCPAgent(
        name="AutogenWorker",
        transport=autogen_transport,
        client_mode=True,
        system_message="I help with text analysis and summarization",
        llm_config={
            "config_list": [{
                "model": "gpt-3.5-turbo",
                "api_key": api_key
            }]
        }
    )
    
    # Create and setup Langchain agent
    langchain_agent, agent_executor = await setup_langchain_agent()
    
    # Create Langchain worker agent with adapter
    langchain_worker = LangchainMCPAdapter(
        name="LangchainWorker",
        transport=langchain_transport,
        client_mode=True,
        langchain_agent=langchain_agent,
        agent_executor=agent_executor
    )
    
    # Start the coordinator server
    print("Starting coordinator server...")
    coordinator.run()
    
    # Give the server a moment to start
    await asyncio.sleep(2)
    
    # Start workers first
    print("Starting workers...")
    autogen_worker.run()
    langchain_worker.run()
    
    # Give workers a moment to start
    await asyncio.sleep(2)
    
    # Connect workers to coordinator
    print("Connecting workers to coordinator...")
    await autogen_worker.connect_to_server("http://localhost:8000")
    await langchain_worker.connect_to_server("http://localhost:8000")
    
    # Example collaborative task
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
    
    print("Assigning tasks to agents...")
    
    # Store task dependencies
    coordinator.task_dependencies = {}
    for step in task["steps"]:
        task_id = step["task_id"]
        coordinator.task_dependencies[task_id] = {
            "url": step["url"],
            "depends_on": [dep for dep in step.get("depends_on", [])]
        }
    
    print(f"Task dependencies: {coordinator.task_dependencies}")
    
    # Assign tasks to agents
    for step in task["steps"]:
        await coordinator.assign_task(step["url"], {
            "task_id": step["task_id"],
            "description": step["description"],
            "reply_to": "http://localhost:8000"
        })
    
    # Keep checking for task completion
    print("Tasks assigned. Waiting for results...")
    try:
        while True:
            if await check_task_completion(coordinator, task):
                print("\nWaiting for final summary...")
                await asyncio.sleep(5)  # Wait for final summary
                if "final_summary" in coordinator.task_results:
                    print("\n=== Final Summary ===")
                    print(coordinator.task_results["final_summary"])
                    print("\nAll tasks completed successfully. Shutting down...")
                    break
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
