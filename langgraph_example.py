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
from mcp_langgraph import MCPNode, MCPReactAgent, create_mcp_langgraph

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
        
        # Create MCP nodes
        researcher = MCPNode(name="Researcher")
        researcher.register_custom_tool(
            name="search_database", 
            description="Search a database for information",
            func=search_database
        )
        
        # Register a tool node for search_database
        search_tool_node = ToolNode(search_database)
        
        # Create the planner agent with MCP
        planner = MCPReactAgent(
            name="Planner",
            system_message="You are a helpful assistant that creates plans based on user requests."
        )
        
        # Register the researcher as a tool for the planner
        def call_researcher(query: str) -> str:
            """Ask the researcher agent to find information."""
            result = researcher.execute_tool("search_database", query=query)
            researcher.update_context("last_search", {
                "query": query,
                "result": result
            })
            return result
        
        planner.register_custom_tool(
            name="ask_researcher",
            description="Ask the researcher to find information",
            func=call_researcher
        )
        
        # Create the coordinator agent that manages the workflow
        coordinator = MCPReactAgent(
            name="Coordinator",
            system_message="You are a coordinator that manages the overall workflow."
        )
        
        # Create a planner node with the MCP agent's tools
        planner_agent = planner.create_agent(self.llm, [call_researcher])
        
        # Build the graph
        builder = langgraph.graph.StateGraph(Dict)
        
        # Add the nodes
        builder.add_node("coordinator", coordinator.create_agent(self.llm))
        builder.add_node("planner", planner_agent)
        builder.add_node("search_database", search_tool_node)
        builder.add_node("notify_user", ToolNode(notify_user))
        
        # Add edges
        builder.add_edge("coordinator", "planner")
        builder.add_edge("planner", "search_database")
        builder.add_edge("search_database", "planner")
        builder.add_edge("planner", "coordinator")
        builder.add_edge("coordinator", "notify_user")
        builder.add_edge("notify_user", "coordinator")
        
        # Set entry point
        builder.set_entry_point("coordinator")
        
        # Add conditional edges for the coordinator
        builder.add_conditional_edges(
            "coordinator",
            lambda state: state.get("next", "planner") if "next" in state else END,
            {
                "planner": "planner",
                END: END
            }
        )
        
        # Compile the graph
        graph = builder.compile()
        
        # Add shared context
        print("1. Setting up shared context")
        coordinator_mcp = coordinator
        planner_mcp = planner
        
        # Add user preferences to both agents' context
        user_preferences = {
            "name": "Bob",
            "location": "San Francisco",
            "preferred_activities": ["dining", "outdoor activities"],
            "dietary_restrictions": ["vegetarian"]
        }
        
        coordinator_mcp.update_context("user_preferences", user_preferences)
        planner_mcp.update_context("user_preferences", user_preferences)
        
        # Run the graph
        print("2. Running the multi-node graph with a user query")
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
        
        # Check context sharing
        print("\n3. Verifying context was shared between nodes")
        coordinator_context = coordinator_mcp.execute_tool("context_list")
        planner_context = planner_mcp.execute_tool("context_list")
        researcher_context = researcher.execute_tool("context_list")
        
        print(f"Coordinator context keys: {coordinator_context['keys']}")
        print(f"Planner context keys: {planner_context['keys']}")
        print(f"Researcher context keys: {researcher_context['keys']}")
        
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