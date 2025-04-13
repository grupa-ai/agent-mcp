"""
Example demonstrating the simple one-line integration with AgentMCP.
"""

from agent_mcp import mcp_agent
from agent_mcp.mcp_decorator import register_tool

# Example 1: Simple class-level integration
@mcp_agent(name="SimpleAgent")
class MyAgent:
    def generate_response(self, message: str) -> str:
        return f"Received: {message}"
    
    @register_tool("greet", "Send a greeting message")
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"

# Example 2: More complex agent with custom tools
@mcp_agent(
    name="CalculatorAgent",
    #system_message="I am a calculator agent that can perform basic math operations."
)
class CalculatorAgent:
    @register_tool("add", "Add two numbers")
    def add(self, a: float, b: float) -> float:
        return a + b
    
    @register_tool("multiply", "Multiply two numbers")
    def multiply(self, a: float, b: float) -> float:
        return a * b

def main():
    # Create instances of our MCP-enabled agents
    simple_agent = MyAgent()
    calc_agent = CalculatorAgent()
    
    # Test the agents
    print("Testing SimpleAgent:")
    print(simple_agent.generate_response("Hello!"))
    print(simple_agent.greet("User"))
    
    print("\nTesting CalculatorAgent:")
    print(f"2 + 3 = {calc_agent.add(2, 3)}")
    print(f"4 * 5 = {calc_agent.multiply(4, 5)}")
    
    # Show available MCP tools for each agent
    print("\nSimpleAgent MCP tools:", simple_agent.mcp_tools.keys())
    print("CalculatorAgent MCP tools:", calc_agent.mcp_tools.keys())

if __name__ == "__main__":
    main()
