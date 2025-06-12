"""
Example of using the @mcp_agent decorator with different frameworks,
and direct instantiation of framework adapters.
"""

import os
import asyncio
from dotenv import load_dotenv
from agent_mcp.mcp_decorator import mcp_agent
from agent_mcp import ArgoAgentMcpAdapter, PlaceholderArgoAgent
from agent_mcp import LlamaIndexMcpAdapter, PlaceholderLlamaIndexAgent

# Load environment variables
load_dotenv()

# Set up OpenAI API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Example 1: LangChain Agent (Decorator Style)
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain.schema.messages import SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

@mcp_agent(name="LangChainResearcher")
class LangChainResearchAgent:
    def __init__(self):
        # Set up LangChain components
        self.llm = ChatOpenAI(model="gpt-3.5-turbo")
        self.tools = [DuckDuckGoSearchRun()]
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a research agent that uses search tools."),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create the agent
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools)
    
    def research(self, query: str) -> str:
        """Perform research on a given query"""
        return self.agent_executor.invoke({"input": query})["output"]

# Example 2: LangGraph Agent (Decorator Style)
from langgraph.graph import Graph, StateGraph
from typing import Dict, TypedDict, Annotated

# Define the state type
class GraphState(TypedDict):
    input: str
    analysis: str
    output: str

@mcp_agent(name="LangGraphAnalyzer")
class LangGraphAnalysisAgent:
    def __init__(self):
        # Set up LangGraph components
        self.llm = ChatOpenAI(model="gpt-3.5-turbo")
        
        # Define the workflow graph
        self.workflow = StateGraph(GraphState)
        
        # Add nodes to the graph
        self.workflow.add_node("analyze", self.analyze_step)
        self.workflow.add_node("summarize", self.summarize_step)
        
        # Add edges
        self.workflow.add_edge("analyze", "summarize")
        self.workflow.set_entry_point("analyze")
        self.workflow.set_finish_point("summarize")
        
        # Compile the graph
        self.graph = self.workflow.compile()
    
    def analyze_step(self, state):
        """Analyze the input data"""
        analysis = self.llm.invoke(f"Analyze this topic: {state['input']}")
        state['analysis'] = analysis
        return state
    
    def summarize_step(self, state):
        """Summarize the analysis"""
        summary = self.llm.invoke(f"Summarize this analysis: {state['analysis']}")
        state['output'] = summary
        return state
    
    def process(self, topic: str) -> str:
        """Process a topic through the LangGraph workflow"""
        result = self.graph.invoke({"input": topic})
        return result["output"]

# Example 3: Argo Agent Adapter (Direct Instantiation)
async def run_argo_adapter_example():
    print("\n--- Running Argo Agent MCP Adapter Example ---")
    # 1. Initialize a (Placeholder) Argo Agent
    argo_bot = PlaceholderArgoAgent(name="DemoArgoBot")

    # 2. Initialize the Adapter
    # Transport is not strictly needed for this basic instantiation example,
    # but would be required for actual communication.
    argo_mcp_adapter = ArgoAgentMcpAdapter(
        name="ArgoDemoAdapter",
        argo_agent=argo_bot,
        client_mode=True # Typical for an agent connecting to a network/coordinator
    )
    print(f"Initialized {argo_mcp_adapter.name} with agent {argo_bot.name}")
    print(f"System message: {argo_mcp_adapter.system_message}")

    # Simulate a task that would normally come via MCP transport
    mock_task_desc = "Plan a three-day trip to Mars."
    print(f"Simulating task execution for: '{mock_task_desc}'")

    # The process_tasks loop would handle this if a message was received.
    # Here, we directly call the agent's method for demonstration of capability.
    # This bypasses the MCP layer for this direct call.
    if hasattr(argo_bot, 'arun'): # Check if the placeholder has 'arun'
        simulated_result = await argo_bot.arun(task_description=mock_task_desc)
        print(f"Simulated result from Argo agent: {simulated_result}")
    else:
        print("PlaceholderArgoAgent does not have 'arun' method for direct simulation in this example.")

    # To see the full MCP interaction, one would normally:
    # 1. Start the adapter's run() loop (e.g., asyncio.create_task(argo_mcp_adapter.run()))
    # 2. Have a transport mechanism configured.
    # 3. Send an MCP 'task' message to this adapter.
    # For this basic example, we're just showing instantiation.
    print("--- Argo Agent MCP Adapter Example Complete ---")


# Example 4: LlamaIndex Adapter (Direct Instantiation)
async def run_llama_index_adapter_example():
    print("\n--- Running LlamaIndex MCP Adapter Example ---")
    # 1. Initialize a (Placeholder) LlamaIndex Agent
    llama_bot = PlaceholderLlamaIndexAgent(name="DemoLlamaBot")

    # 2. Initialize the Adapter
    llama_mcp_adapter = LlamaIndexMcpAdapter(
        name="LlamaDemoAdapter",
        llama_index_agent=llama_bot,
        client_mode=True,
        execution_method_name="chat" # Can be "chat" or "query" for the placeholder
    )
    print(f"Initialized {llama_mcp_adapter.name} with agent {llama_bot.name} (method: {llama_mcp_adapter.execution_method_name})")
    print(f"System message: {llama_mcp_adapter.system_message}")

    mock_query = "What is the capital of France?"
    print(f"Simulating '{llama_mcp_adapter.execution_method_name}' execution for: '{mock_query}'")

    agent_method = getattr(llama_bot, llama_mcp_adapter.execution_method_name)
    simulated_response = await agent_method(mock_query) # This returns the mock response object

    # The adapter's process_tasks would normally convert this to string.
    print(f"Simulated response from LlamaIndex agent: {str(simulated_response)}")
    
    print("--- LlamaIndex MCP Adapter Example Complete ---")

async def main():
    print("Testing LangChain Agent (Decorator Style):")
    langchain_agent = LangChainResearchAgent()
    # For decorated agents, the research method is directly callable.
    # If it were an MCP tool, you'd use `langchain_agent.mcp_call_tool('research', query=...)`
    # but research is not auto-registered as a tool unless specified.
    # Let's assume we want to test its core logic here.
    result_lc = langchain_agent.research("Latest developments in quantum computing 2025")
    print(f"Research result: {result_lc}")
    # print(f"Available MCP tools: {langchain_agent.mcp_tools.keys()}\n") # mcp_tools is on the adapter

    print("\nTesting LangGraph Agent (Decorator Style):")
    langgraph_agent = LangGraphAnalysisAgent()
    result_lg = langgraph_agent.process("Impact of AI on healthcare in 2025")
    print(f"Analysis result: {result_lg}")
    # print(f"Available MCP tools: {langgraph_agent.mcp_tools.keys()}")

    # Run new adapter examples
    await run_argo_adapter_example()
    await run_llama_index_adapter_example()

# Example usage
if __name__ == "__main__":
    asyncio.run(main())
