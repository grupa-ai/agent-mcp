"""
LangGraph Example using MCPNode.

This example demonstrates the use of Model Context Protocol with LangGraph,
showing how to build agent graphs with shared context and dynamic behavior.
"""

import os
import json
from typing import Dict, List, Any

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
import langgraph.graph
from langgraph.graph import END
from langgraph.prebuilt import ToolNode
from openai import OpenAI

# Import our MCP implementation for LangGraph
from agent_mcp.mcp_langgraph import MCPNode, MCPReactAgent, create_mcp_langgraph

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)


def get_llm():
    """Get the OpenAI LLM wrapper that implements the langchain interface."""
    from langchain_openai import ChatOpenAI
    
    # Initialize with the newest model (gpt-4o) which was released after your knowledge cutoff
    return ChatOpenAI(model="gpt-4o", temperature=0.7)


class LangGraphExample:
    """Demonstration of the MCP protocol with LangGraph."""
    
    def __init__(self):
        """Initialize the LangGraph Example with MCP capabilities."""
        self.llm = get_llm()
        
    def run_simple_example(self):
        """Run a simple example of MCP with LangGraph."""
        print("=== Simple MCP LangGraph Example ===")
        
        # Create a graph with MCP capabilities
        graph = create_mcp_langgraph(
            self.llm,
            name="SimpleMCPGraph",
            system_message="You are a helpful assistant that uses context to answer questions."
        )
        
        # Access the MCP agent for the graph
        mcp_agent = graph.mcp_agent
        
        # Add context to the MCP agent
        print("1. Adding context to the MCP agent")
        mcp_agent.update_context("user_info", {
            "name": "Alice",
            "occupation": "Data Scientist",
            "interests": ["AI", "machine learning", "hiking"]
        })
        mcp_agent.update_context("current_weather", {
            "location": "San Francisco",
            "condition": "Sunny",
            "temperature": 72
        })
        
        # List the available context
        print("2. Listing available context")
        context_list = mcp_agent.execute_tool("context_list")
        print(f"Available context keys: {json.dumps(context_list['keys'], indent=2)}")
        
        # Run the graph with a user question
        print("3. Running the graph with a user query")
        question = "What outdoor activities would you recommend for me today?"
        
        # Create the initial state
        initial_state = {"messages": [HumanMessage(content=question)]}
        
        # Execute the graph
        result = graph.invoke(initial_state)
        
        # Print the response
        ai_message = next(msg for msg in result["messages"] if isinstance(msg, AIMessage))
        print(f"User: {question}")
        print(f"Agent: {ai_message.content}")
        
        # Update context through a tool call
        print("\n4. Updating context through a tool call")
        new_state = {
            "messages": result["messages"] + [
                HumanMessage(content="Please add 'mountain biking' to my interests.")
            ]
        }
        
        result = graph.invoke(new_state)
        
        # Print the response
        ai_message = next(msg for msg in result["messages"] if isinstance(msg, AIMessage))
        print("User: Please add 'mountain biking' to my interests.")
        print(f"Agent: {ai_message.content}")
        
        # Get the updated user info
        print("\n5. Getting the updated user info")
        user_info = mcp_agent.get_context("user_info")
        print(f"Updated user info: {json.dumps(user_info, indent=2)}")
        
        print("\nSimple MCP LangGraph Example completed.")
    
    def run_multi_node_example(self):
        """Run an example with multiple nodes sharing context."""
        print("\n=== Multi-Node MCP LangGraph Example ===")
        
        # Create custom tools
        @tool("search_database")
        def search_database(query: str) -> str:
            """Search a database for information."""
            # Simulate database search
            if "weather" in query.lower():
                return json.dumps({
                    "result": "Found weather data for San Francisco: Sunny, 72°F"
                })
            elif "restaurants" in query.lower():
                return json.dumps({
                    "result": "Found 5 restaurants near downtown: Sushi Place, Burger Joint, Italian Corner, Thai Spice, Taco Shop"
                })
            else:
                return json.dumps({
                    "result": f"No specific data found for: {query}"
                })
        
        @tool("notify_user")
        def notify_user(message: str) -> str:
            """Send a notification to the user."""
            return json.dumps({
                "status": "success",
                "message": f"Notification sent: {message}"
            })
        
        # SIMPLIFIED APPROACH: Use a single MCP agent with all tools
        # This avoids recursion issues in the graph
        print("1. Creating a unified MCP agent with all tools")
        agent = MCPReactAgent(
            name="UnifiedAgent",
            system_message="You are a helpful assistant that can research information and make recommendations."
        )
        
        # Register all tools with the agent
        agent.register_custom_tool(
            name="search_database", 
            description="Search a database for information",
            func=search_database
        )
        
        agent.register_custom_tool(
            name="notify_user",
            description="Send a notification to the user",
            func=notify_user
        )
        
        # Create a simple graph with just one node
        builder = langgraph.graph.StateGraph(Dict)
        
        # Add the single node
        builder.add_node("agent", agent.create_agent(self.llm))
        
        # Set entry point
        builder.set_entry_point("agent")
        
        # Simple edge - just go to END after the agent responds
        builder.add_edge("agent", END)
        
        # Compile the graph
        graph = builder.compile()
        
        # Add context to the agent
        print("2. Setting up context")
        user_preferences = {
            "name": "Bob",
            "location": "San Francisco",
            "preferred_activities": ["dining", "outdoor activities"],
            "dietary_restrictions": ["vegetarian"]
        }
        
        agent.update_context("user_preferences", user_preferences)
        
        # Run the graph
        print("3. Running the graph with a user query")
        initial_state = {
            "messages": [
                HumanMessage(content="I'd like recommendations for activities today, including places to eat.")
            ]
        }
        
        # Execute the workflow
        result = graph.invoke(initial_state)
        
        # Print the final response
        messages = result.get("messages", [])
        last_ai_message = next((msg for msg in reversed(messages) if isinstance(msg, AIMessage)), None)
        
        if last_ai_message:
            print(f"Final response: {last_ai_message.content}")
        
        # Check context 
        print("\n4. Verifying context")
        context = agent.execute_tool("context_list")
        
        print(f"Agent context keys: {context['keys']}")
        
        print("\nMulti-Node MCP LangGraph Example completed.")


def main():
    """Run the LangGraph examples."""
    print("Starting LangGraph MCP Examples...")
    
    example = LangGraphExample()
    example.run_simple_example()
    example.run_multi_node_example()
    
    print("\nAll LangGraph MCP Examples completed successfully.")


if __name__ == "__main__":
    main()