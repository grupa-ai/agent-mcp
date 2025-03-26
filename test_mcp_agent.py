"""
Test module for MCPAgent.

This module provides testing capabilities for the MCPAgent class,
demonstrating its MCP capabilities and basic interaction with AutoGen.
"""

import json
from typing import Dict, List, Any, Optional

# Import MCPAgent from the mcp_agent module
from mcp_agent import MCPAgent


def test_basic_mcp_functionality():
    """Test basic MCP agent functionality."""
    print("=== Testing Basic MCP Functionality ===")
    
    # Create an MCP-enabled agent (no LLM config needed for basic tests)
    mcp_agent = MCPAgent(
        name="MCP_Assistant",
        system_message="You are an MCP-enabled assistant that can manage context."
    )
    
    # Test context operations
    print("\nTesting context operations:")
    
    # Set context
    result = mcp_agent.execute_tool("context.set", key="user_name", value="Alice")
    print(f"Set context: {result}")
    
    # Get context
    result = mcp_agent.execute_tool("context.get", key="user_name")
    print(f"Get context: {result}")
    
    # List context
    result = mcp_agent.execute_tool("context.list")
    print(f"List context: {result}")
    
    # Remove context
    result = mcp_agent.execute_tool("context.remove", key="user_name")
    print(f"Remove context: {result}")
    
    # Check context was removed
    result = mcp_agent.execute_tool("context.list")
    print(f"List context after removal: {result}")
    
    # Test MCP info
    result = mcp_agent.execute_tool("mcp.info")
    print(f"\nMCP info: {json.dumps(result, indent=2)}")


def test_custom_tool_registration():
    """Test registering and using custom MCP tools."""
    print("\n=== Testing Custom Tool Registration ===")
    
    # Create an MCP-enabled agent (no LLM config needed for basic tests)
    mcp_agent = MCPAgent(
        name="Tool_Agent"
    )
    
    # Define a custom tool function
    def calculate_sum(self, a: int, b: int) -> Dict[str, Any]:
        """Calculate the sum of two numbers."""
        result = a + b
        return {"status": "success", "result": result}
    
    # Register the custom tool
    mcp_agent.register_mcp_tool(
        name="math.sum",
        description="Calculate the sum of two numbers",
        func=calculate_sum,
        a_description="First number to add",
        b_description="Second number to add"
    )
    
    # Test the custom tool
    result = mcp_agent.execute_tool("math.sum", a=5, b=7)
    print(f"Custom tool result: {result}")
    
    # Check that the tool appears in the available tools list
    tool_list = mcp_agent.list_available_tools()
    print("\nAvailable tools:")
    for tool in tool_list:
        print(f"- {tool['name']}: {tool['description']}")


def test_multiple_context_operations():
    """Test more complex context operations."""
    print("\n=== Testing Multiple Context Operations ===")
    
    # Create an MCP-enabled agent
    mcp_agent = MCPAgent(
        name="Context_Agent"
    )
    
    # Add multiple context items
    print("Adding multiple context items:")
    
    mcp_agent.update_context("user", {
        "name": "Bob",
        "email": "bob@example.com",
        "preferences": {
            "theme": "dark",
            "notifications": True
        }
    })
    print("Added user context")
    
    mcp_agent.update_context("weather", {
        "location": "New York",
        "temperature": 65,
        "conditions": "Partly Cloudy"
    })
    print("Added weather context")
    
    mcp_agent.update_context("tasks", [
        "Complete project proposal",
        "Schedule meeting with clients",
        "Review quarterly reports"
    ])
    print("Added tasks context")
    
    # List all context keys
    result = mcp_agent.execute_tool("context.list")
    print(f"\nAll context keys: {result}")
    
    # Generate context summary
    summary = mcp_agent._generate_context_summary()
    print(f"\nContext summary:\n{summary}")
    
    # Get specific context
    result = mcp_agent.get_context("user")
    print(f"\nUser context: {result}")


def test_agent_as_tool_simulation():
    """Simulate registering and using an agent as a tool."""
    print("\n=== Testing Agent as Tool (Simulation) ===")
    
    # Create a simple agent that will be registered as a tool
    helper_agent = MCPAgent(
        name="HelperAgent",
        system_message="I am a helper agent that assists with various tasks."
    )
    
    # Create our main MCP agent
    coordinator = MCPAgent(
        name="Coordinator",
        system_message="I am a coordinator that delegates tasks to other agents."
    )
    
    # Register the helper agent as a tool
    coordinator.register_agent_as_tool(helper_agent)
    
    # Check that the agent tool was registered
    tool_list = coordinator.list_available_tools()
    print("Available tools for coordinator:")
    for tool in tool_list:
        if tool["name"].startswith("agent."):
            print(f"- {tool['name']}: {tool['description']}")
    
    # This would normally make a real call, but in this simulation we'll just show the mechanism
    print("\nAgent tool call would execute with these parameters:")
    print("- Agent: HelperAgent")
    print("- Message: 'Can you help me analyze this data?'")
    print("- Response would be returned to the Coordinator")


def main():
    """Run all tests."""
    # Run tests that don't require an API key
    test_basic_mcp_functionality()
    test_custom_tool_registration()
    test_multiple_context_operations()
    test_agent_as_tool_simulation()
    
    print("\n=== All tests completed successfully ===")
    print("Note: These tests demonstrate the MCP functionality without requiring an actual LLM.")
    print("For a full demonstration with LLM responses, you would need to provide an OpenAI API key.")


if __name__ == "__main__":
    main()
