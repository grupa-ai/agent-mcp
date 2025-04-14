"""
MCP Features Demo

This script demonstrates the key features of the Model Context Protocol
implementation in MCPAgent with detailed explanations of what's happening
at each step.
"""

import os
import json
from typing import Dict, List, Any, Optional

# Import MCPAgent
from agent_mcp.mcp_agent import MCPAgent

# Check for API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

# LLM configuration - using gpt-3.5-turbo for faster responses
config = {
    "config_list": [{"model": "gpt-3.5-turbo", "api_key": api_key}],
}

def demonstrate_context_operations():
    """Demonstrate basic context operations with MCPAgent."""
    print("\n=== Demonstrating Context Operations ===")
    
    # Create a simple MCP agent without LLM
    agent = MCPAgent(
        name="ContextDemo",
        system_message="You demonstrate context operations."
    )
    
    # 1. Set context using direct method
    print("\n1. Setting context using direct update_context() method")
    agent.update_context("user", {
        "name": "Alice",
        "preferences": {
            "color": "blue",
            "language": "English",
            "notifications": True
        }
    })
    print("User context added")
    
    # 2. Get context using direct method
    print("\n2. Getting context using direct get_context() method")
    user_context = agent.get_context("user")
    print(f"Retrieved user context: {json.dumps(user_context, indent=2)}")
    
    # 3. Set context using MCP tool
    print("\n3. Setting context using context_set tool")
    result = agent.execute_tool(
        "context_set", 
        key="weather", 
        value={"location": "New York", "temperature": 72, "conditions": "Sunny"}
    )
    print(f"Tool result: {result}")
    
    # 4. Get context using MCP tool
    print("\n4. Getting context using context_get tool")
    result = agent.execute_tool("context_get", key="weather")
    print(f"Tool result: {json.dumps(result, indent=2)}")
    
    # 5. List all context keys
    print("\n5. Listing all context keys using context_list tool")
    result = agent.execute_tool("context_list")
    print(f"Tool result: {json.dumps(result, indent=2)}")
    
    # 6. Demonstrate context summary generation
    print("\n6. Generating context summary for LLM integration")
    summary = agent._generate_context_summary()
    print(f"Context summary:\n{summary}")
    
    # 7. Remove context using MCP tool
    print("\n7. Removing context using context_remove tool")
    result = agent.execute_tool("context_remove", key="weather")
    print(f"Tool result: {json.dumps(result, indent=2)}")
    
    # 8. Verify context was removed
    print("\n8. Verifying context was removed by listing keys again")
    result = agent.execute_tool("context_list")
    print(f"Tool result: {json.dumps(result, indent=2)}")

def demonstrate_custom_tools():
    """Demonstrate registering and using custom tools with MCPAgent."""
    print("\n=== Demonstrating Custom Tool Registration ===")
    
    # Create a simple MCP agent
    agent = MCPAgent(
        name="ToolDemo",
        system_message="You demonstrate tool operations."
    )
    
    # 1. Define and register a simple calculator tool
    print("\n1. Defining and registering a calculator tool")
    
    def calculate(operation: str, a: float, b: float) -> Dict:
        """Perform a basic calculation."""
        result = None
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return {"status": "error", "message": "Cannot divide by zero"}
            result = a / b
        else:
            return {"status": "error", "message": f"Unknown operation: {operation}"}
            
        return {"status": "success", "result": result}
    
    # Register the tool with parameter descriptions
    agent.register_mcp_tool(
        name="math_calculate",
        description="Perform basic mathematical calculations",
        func=calculate,
        operation_description="The operation to perform: add, subtract, multiply, or divide",
        a_description="First number",
        b_description="Second number"
    )
    print("Calculator tool registered")
    
    # 2. Define and register a text processing tool
    print("\n2. Defining and registering a text processing tool")
    
    def process_text(text: str, operation: str) -> Dict:
        """Process text with various operations."""
        if operation == "uppercase":
            return {"status": "success", "result": text.upper()}
        elif operation == "lowercase":
            return {"status": "success", "result": text.lower()}
        elif operation == "capitalize":
            return {"status": "success", "result": text.capitalize()}
        elif operation == "word_count":
            return {"status": "success", "result": len(text.split())}
        else:
            return {"status": "error", "message": f"Unknown operation: {operation}"}
    
    # Register the tool
    agent.register_mcp_tool(
        name="text_process",
        description="Process text with various operations",
        func=process_text,
        text_description="The text to process",
        operation_description="The operation to perform: uppercase, lowercase, capitalize, or word_count"
    )
    print("Text processing tool registered")
    
    # 3. Get information about all tools
    print("\n3. Getting information about all available tools")
    tool_info = agent.execute_tool("mcp_info")
    print(f"Agent ID: {tool_info['id']}")
    print(f"Agent Name: {tool_info['name']}")
    print(f"MCP Version: {tool_info['version']}")
    print("Available tools:")
    for tool in tool_info['tools']:
        print(f"- {tool['name']}: {tool['description']}")
        if tool['parameters']:
            for param in tool['parameters']:
                required = "required" if param.get('required', False) else "optional"
                print(f"  • {param['name']} ({required}): {param['description']}")
    
    # 4. Use the calculator tool
    print("\n4. Using the calculator tool")
    result = agent.execute_tool("math_calculate", operation="add", a=5, b=7)
    print(f"5 + 7 = {json.dumps(result, indent=2)}")
    
    result = agent.execute_tool("math_calculate", operation="multiply", a=6, b=8)
    print(f"6 * 8 = {json.dumps(result, indent=2)}")
    
    # 5. Use the text processing tool
    print("\n5. Using the text processing tool")
    result = agent.execute_tool("text_process", text="Hello World", operation="uppercase")
    print(f"Uppercase: {json.dumps(result, indent=2)}")
    
    result = agent.execute_tool("text_process", text="Hello World", operation="word_count")
    print(f"Word count: {json.dumps(result, indent=2)}")

def demonstrate_agent_as_tool():
    """Demonstrate registering and using an agent as a tool."""
    print("\n=== Demonstrating Agent-as-Tool ===")
    
    # 1. Create two MCP agents
    print("\n1. Creating a helper agent and a main agent")
    
    helper = MCPAgent(
        name="HelperAgent",
        system_message="You are a helpful assistant that specializes in providing definitions and explanations."
    )
    
    # Give the helper some context to use
    helper.update_context("definitions", {
        "Machine Learning": "A field of study that gives computers the ability to learn without being explicitly programmed.",
        "Neural Network": "A computing system inspired by biological neural networks that can learn to perform tasks by analyzing examples.",
        "Context Protocol": "A standardized way for AI systems to share and manage context information."
    })
    
    main_agent = MCPAgent(
        name="MainAgent",
        system_message="You are a coordinator that can ask other agents for help."
    )
    
    # 2. Register the helper agent as a tool
    print("\n2. Registering the helper agent as a tool for the main agent")
    main_agent.register_agent_as_tool(helper)
    print("Helper agent registered as a tool")
    
    # 3. List all tools on the main agent
    print("\n3. Listing all tools available to the main agent")
    tool_info = main_agent.execute_tool("mcp_info")
    print("Available tools:")
    for tool in tool_info['tools']:
        print(f"- {tool['name']}: {tool['description']}")
    
    # 4. Use the agent tool
    print("\n4. Using the agent tool to ask for a definition")
    result = main_agent.execute_tool(
        "agent_HelperAgent", 
        message="Can you define what Neural Network means?"
    )
    print(f"Response from helper: {json.dumps(result, indent=2)}")
    
    # 5. Show how context is maintained in the helper
    print("\n5. Adding more context to the helper agent")
    helper.update_context("definitions", {
        "Machine Learning": "A field of study that gives computers the ability to learn without being explicitly programmed.",
        "Neural Network": "A computing system inspired by biological neural networks that can learn to perform tasks by analyzing examples.",
        "Context Protocol": "A standardized way for AI systems to share and manage context information.",
        "Deep Learning": "A subset of machine learning that uses multi-layered neural networks to model complex patterns."
    })
    
    print("\n6. Asking for a new definition that was just added")
    result = main_agent.execute_tool(
        "agent_HelperAgent", 
        message="What is Deep Learning?"
    )
    print(f"Response from helper: {json.dumps(result, indent=2)}")

def demonstrate_llm_integration():
    """Demonstrate using MCPAgent with a real LLM."""
    print("\n=== Demonstrating LLM Integration ===")
    
    # Skip if no API key
    if not api_key:
        print("Skipping LLM demo - no API key provided")
        return
    
    # 1. Create an MCP agent with LLM capability
    print("\n1. Creating an MCP agent with LLM capability")
    agent = MCPAgent(
        name="LLMAgent",
        system_message="You are a helpful assistant that uses context to enhance your responses.",
        llm_config=config
    )
    print("Agent created with LLM capability")
    
    # 2. Add context that will be used by the LLM
    print("\n2. Adding context about the user and weather")
    agent.update_context("user", {
        "name": "Bob",
        "location": "San Francisco",
        "interests": ["hiking", "photography", "cooking"]
    })
    
    agent.update_context("weather", {
        "location": "San Francisco",
        "current": {
            "temperature": 68,
            "conditions": "Partly cloudy",
            "wind": "Light breeze"
        },
        "forecast": ["Sunny", "Sunny", "Rain", "Partly cloudy"]
    })
    print("Context added")
    
    # 3. Test with a prompt that should use the context
    print("\n3. Testing with a prompt that should use context")
    prompt = "What's the weather like today and what activities would you recommend for me?"
    
    print(f"User: {prompt}")
    response = agent.generate_reply(
        messages=[{"role": "user", "content": prompt}]
    )
    print(f"Agent: {response}")
    
    # 4. Add a tool call to update context
    print("\n4. Adding a new interest through natural language")
    prompt = "Please add 'tennis' to my list of interests."
    
    print(f"User: {prompt}")
    response = agent.generate_reply(
        messages=[{"role": "user", "content": prompt}]
    )
    print(f"Agent: {response}")
    
    # Manual detection since it might not work automatically
    user_context = agent.get_context("user")
    if user_context and "interests" in user_context and isinstance(user_context["interests"], list):
        if "tennis" not in user_context["interests"]:
            user_context["interests"].append("tennis")
            agent.update_context("user", user_context)
            print("Manually added 'tennis' to interests")
    
    # 5. Check if the context was updated
    print("\n5. Checking if context was updated")
    user_context = agent.get_context("user")
    print(f"Updated user context: {json.dumps(user_context, indent=2)}")
    
    # 6. Ask about the updated interests
    print("\n6. Asking about updated interests")
    prompt = "What are my interests now?"
    
    print(f"User: {prompt}")
    response = agent.generate_reply(
        messages=[{"role": "user", "content": prompt}]
    )
    print(f"Agent: {response}")

def main():
    """Run the MCP features demonstration."""
    print("=== MCP Features Demonstration ===")
    print("This script shows the key features of the MCPAgent with detailed explanations.")
    
    # Demonstrate basic context operations
    demonstrate_context_operations()
    
    # Demonstrate custom tools
    demonstrate_custom_tools()
    
    # Demonstrate agent as tool
    demonstrate_agent_as_tool()
    
    # Demonstrate LLM integration
    demonstrate_llm_integration()
    
    print("\n=== Demonstration Complete ===")
    print("You've now seen the main features of MCPAgent:")
    print("1. Context management (get, set, list, remove)")
    print("2. Custom tool registration and usage")
    print("3. Using agents as tools")
    print("4. LLM integration with context")
    print("\nTo run the more interactive examples, try:")
    print("- agent_network_example.py: A social network of agents")
    print("- collaborative_task_example.py: A team of agents working on a project")

if __name__ == "__main__":
    main()