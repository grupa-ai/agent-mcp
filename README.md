# MCPAgent for AutoGen

## Overview

MCPAgent is a powerful extension to AutoGen's agent architecture that implements the Model Context Protocol (MCP). It enables seamless context sharing, standardized tool usage, and transparent interaction between agents and LLMs.

This implementation allows developers to easily create MCP-capable agents by simply inheriting from the MCPAgent class.

## Features

- **Transparent MCP Implementation**: Extends AutoGen's ConversableAgent with full MCP support
- **Context Management**: Built-in tools for managing, accessing, and sharing context
- **Tool Registration**: Easy registration of functions as MCP-compatible tools
- **Agent Integration**: Register other agents as callable tools
- **Multi-format Tool Calls**: Support for OpenAI function calls, explicit MCP calls, and natural language intent detection
- **LLM Context Integration**: Automatic inclusion of relevant context in LLM prompts
- **Minimal Configuration**: Simple inheritance pattern matching AutoGen's existing patterns

## Installation

```bash
# First, install AutoGen if you haven't already
pip install autogen

# Then, just include mcp_agent.py in your project
```

## Quick Start

### Creating a Basic MCP Agent

```python
from mcp_agent import MCPAgent

# Create an MCP-enabled agent
agent = MCPAgent(
    name="MyMCPAgent",
    system_message="You are an MCP-enabled assistant"
)

# Add context to the agent
agent.update_context("user", {
    "name": "Alice",
    "preferences": {
        "theme": "dark",
        "language": "English"
    }
})

# Test using an MCP tool directly
result = agent.execute_tool("context_list")
print(f"Available context: {result}")
```

### Using MCPAgent with OpenAI

```python
import os
from mcp_agent import MCPAgent

# Configure LLM
config = {
    "config_list": [{"model": "gpt-3.5-turbo", "api_key": os.environ.get("OPENAI_API_KEY")}],
}

# Create an MCP-enabled agent with LLM capabilities
assistant = MCPAgent(
    name="Assistant",
    system_message="You are an assistant that uses context to enhance responses.",
    llm_config=config
)

# Add context to the assistant
assistant.update_context("weather", {
    "location": "New York",
    "temperature": 72,
    "conditions": "Sunny"
})

# Generate a response that uses the context
response = assistant.generate_reply(
    messages=[{"role": "user", "content": "What's the weather like today?"}]
)
print(f"Assistant: {response}")
```

### Registering Custom Tools

```python
from mcp_agent import MCPAgent

# Create an MCP-enabled agent
agent = MCPAgent(name="ToolAgent")

# Define a custom tool function
def calculate_sum(a: int, b: int):
    """Calculate the sum of two numbers."""
    result = a + b
    return {"status": "success", "result": result}

# Register the custom tool
agent.register_mcp_tool(
    name="math_sum",
    description="Calculate the sum of two numbers",
    func=calculate_sum,
    a_description="First number to add",
    b_description="Second number to add"
)

# Use the custom tool
result = agent.execute_tool("math_sum", a=5, b=7)
print(f"5 + 7 = {result}")
```

### Registering an Agent as a Tool

```python
from mcp_agent import MCPAgent

# Create helper agent
helper = MCPAgent(
    name="Helper",
    system_message="I assist with specialized tasks."
)

# Create coordinator agent
coordinator = MCPAgent(
    name="Coordinator",
    system_message="I delegate tasks to other agents."
)

# Register helper as a tool for the coordinator
coordinator.register_agent_as_tool(helper)

# Now the coordinator can call the helper agent as a tool
```

## Model Context Protocol Support

The MCPAgent implements the Model Context Protocol, which provides a standardized way for AI systems to share context and capabilities. This implementation supports:

### Context Management

```python
# Set context
agent.update_context("key", "value")

# Get context
value = agent.get_context("key")

# List all context keys
keys = agent.execute_tool("context_list")

# Remove context
agent.execute_tool("context_remove", key="key_to_remove")
```

### Tool Call Formats

MCPAgent supports three formats for tool calls:

1. **Direct Method Calls**:
   ```python
   result = agent.execute_tool("tool_name", param1="value1", param2="value2")
   ```

2. **OpenAI Function Call Format**:
   When an LLM generates a function call in the OpenAI format, MCPAgent automatically detects and executes it.

3. **Explicit MCP Call Format**:
   ```
   mcp.call({"tool": "tool_name", "arguments": {"param1": "value1"}})
   ```

4. **Natural Language Intent Detection**:
   Basic support for detecting context operations in natural language (e.g., "Add mountain biking to my interests").

### MCP Information

You can retrieve information about an agent's MCP capabilities:

```python
info = agent.execute_tool("mcp_info")
print(f"Agent ID: {info['id']}")
print(f"Agent Version: {info['version']}")
print(f"Available Tools: {len(info['tools'])}")
```
