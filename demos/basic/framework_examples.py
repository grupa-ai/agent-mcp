"""
Example of using the @mcp_agent decorator with different frameworks.
"""

import os
from dotenv import load_dotenv
from agent_mcp.mcp_decorator import mcp_agent

# Load environment variables
load_dotenv()

# Set up OpenAI API key
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Example 1: LangChain Agent
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

# Example 2: LangGraph Agent
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

# Example usage
if __name__ == "__main__":
    print("Testing LangChain Agent:")
    langchain_agent = LangChainResearchAgent()
    result = langchain_agent.research("Latest developments in quantum computing 2025")
    print(f"Research result: {result}")
    print(f"Available MCP tools: {langchain_agent.mcp_tools.keys()}\n")
    
    print("Testing LangGraph Agent:")
    langgraph_agent = LangGraphAnalysisAgent()
    result = langgraph_agent.process("Impact of AI on healthcare in 2025")
    print(f"Analysis result: {result}")
    print(f"Available MCP tools: {langgraph_agent.mcp_tools.keys()}")
