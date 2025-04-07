# AgentMCP: Multi-Framework Agent Integration Platform

## Overview

AgentMCP is a revolutionary platform that enables seamless integration between different AI agent frameworks (Autogen, Langchain, CrewAI, and LangGraph). It implements the Model Context Protocol (MCP) to provide standardized communication, task orchestration, and context sharing between agents from different ecosystems.

The platform uses a flexible coordinator-worker architecture with HTTP/FastAPI for communication, allowing agents to work together regardless of their underlying framework.

## Features

### Core Features
- **Multi-Framework Support**: Seamlessly integrate agents from:
  - Autogen (Autonomous agents)
  - Langchain (Chain-of-thought reasoning)
  - CrewAI (Role-based collaboration)
  - LangGraph (Workflow orchestration)

### Architecture
- **Coordinator-Worker Pattern**: Centralized task management with distributed execution
- **FastAPI Integration**: Modern, high-performance HTTP communication
- **Asynchronous Processing**: Non-blocking task execution and message handling
- **Flexible Transport Layer**: Extensible communication protocols

### Task Management
- **Dependency Tracking**: Handle complex task dependencies
- **Result Forwarding**: Automatic routing of task results
- **Dynamic Task Assignment**: Intelligent task distribution
- **Progress Monitoring**: Track task completion and status

### Integration Features
- **Framework Adapters**: Convert between framework-specific formats
- **Context Sharing**: Share data between different agent types
- **Tool Registration**: Register and share capabilities across frameworks
- **Error Handling**: Robust error recovery and reporting

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/AgentMCP.git
cd AgentMCP

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies
```
autogen
langchain
langchain-openai
crewai
langgraph
openai
fastapi
uvicorn
aiohttp
sse-starlette
duckduckgo-search
python-dotenv
```

## Quick Start

### 1. Set Up Environment
```bash
# Create .env file
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### 2. Run Multi-Framework Example

```python
# Run the multi-framework example
python multi_framework_example.py
```

This example demonstrates:
- Collaborative research task using multiple frameworks
- Task dependency management
- Inter-framework communication
- Result aggregation and summarization

## Interacting with the Deployed Network Server

Once the MCP Network Server is deployed (e.g., as a Firebase Function), you can interact with its API endpoints using standard HTTP requests. The base URL for the deployed function is: `https://mcp-server-ixlfhxquwq-ew.a.run.app`

### Example: Registering an Agent (using curl)

```bash
# Replace <FUNCTION_URL> with your actual deployed URL if different
FUNCTION_URL="https://mcp-server-ixlfhxquwq-ew.a.run.app"

curl -X POST "${FUNCTION_URL}/register" \
-H "Content-Type: application/json" \
-d '{
  "agent_id": "my_new_agent_007",
  "info": {
    "type": "curl_tester",
    "capabilities": ["test"]
  }
}'
```
This will return a JSON response with the agent's ID and a JWT token required for authenticated endpoints.

### Example: Checking Server Root (using curl)

```bash
# Replace <FUNCTION_URL> with your actual deployed URL if different
FUNCTION_URL="https://mcp-server-ixlfhxquwq-ew.a.run.app"

curl "${FUNCTION_URL}/"
```
This should return `{"message":"MCP Network Server is running!"}`.

### Example: Listing Agents (using curl and a token)

First, register an agent (see above) and get its token. Then:

```bash
# Replace <FUNCTION_URL> and <YOUR_JWT_TOKEN>
FUNCTION_URL="https://mcp-server-ixlfhxquwq-ew.a.run.app"
TOKEN="<YOUR_JWT_TOKEN>" # Replace with the token from the /register response

curl "${FUNCTION_URL}/agents" -H "Authorization: Bearer ${TOKEN}"
```

## Architecture Overview

### Components

1. **Base Classes**
   - `MCPAgent`: Core agent functionality
   - `HTTPTransport`: Communication layer
   - `HeterogeneousGroupChat`: Agent coordination

2. **Framework Adapters**
   - `CrewAIMCPAdapter`: CrewAI integration
   - `LangchainMCPAdapter`: Langchain integration
   - `LangGraphMCPAdapter`: LangGraph integration
   - `EnhancedMCPAgent`: Extended Autogen integration

3. **Task Management**
   ```python
   task = {
       "task_id": "research_project",
       "steps": [
           {
               "agent": "LangchainWorker",
               "task_id": "research",
               "description": "Research topic"
           },
           {
               "agent": "CrewAIWorker",
               "task_id": "analysis",
               "depends_on": ["research"]
           }
       ]
   }
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

## Advanced Examples

The project includes several advanced examples that demonstrate the full potential of MCPAgent:

### 1. MCPFeaturesDemo

Run `python mcp_features_demo.py` to see a step-by-step demonstration of all MCPAgent features:
- Context management operations
- Custom tool registration and usage
- Using agents as tools
- LLM integration with context

This is the best example to start with to understand the core capabilities of MCPAgent.

### 2. Agent Network

Run `python agent_network_example.py` to start an interactive agent network example:
- Simulates a social network of agents
- Each agent has a specialized role (Coordinator, Researcher, Analyst, etc.)
- Agents can communicate with each other through tool calls
- You can interact with any agent and broadcast messages
- Human input is fully supported

This example demonstrates how MCPAgent enables creating complex agent networks where agents can call and interact with each other.

### 3. Collaborative Project

Run `python collaborative_task_example.py` to start a collaborative project simulation:
- Team of agents working together on a shared project
- Shared workspace context with research, analysis, and tasks
- Task assignment and progress tracking
- Full conversation history captured
- Human input for setting topics and interacting with agents

This example showcases how MCPAgent can be used in a structured collaborative environment where agents share a workspace and contribute to a common goal.

## LangGraph Implementation

MCPAgent has also been implemented for LangGraph, providing the same Model Context Protocol capabilities within the LangGraph framework:

```python
from mcp_langgraph import MCPNode, MCPReactAgent, create_mcp_langgraph
from langchain_openai import ChatOpenAI

# Create a LLM
llm = ChatOpenAI(model="gpt-4o")

# Create a LangGraph with MCP capabilities
graph = create_mcp_langgraph(
    llm,
    name="SimpleMCPGraph",
    system_message="You are a helpful assistant that uses context to answer questions."
)

# Access the MCP agent for the graph
mcp_agent = graph.mcp_agent

# Add context to the MCP agent
mcp_agent.update_context("user_info", {
    "name": "Alice",
    "occupation": "Data Scientist"
})

# Run the graph with a user query
from langchain_core.messages import HumanMessage

question = "What should I learn next in my field?"
initial_state = {"messages": [HumanMessage(content=question)]}
result = graph.invoke(initial_state)
```

### LangGraph Examples

The project includes several examples that demonstrate how to use the MCP protocol with LangGraph:

1. **Basic LangGraph Example**
   Run `python langgraph_example.py` to see a step-by-step demonstration of MCPNode with LangGraph.

2. **LangGraph Agent Network**
   Run `python langgraph_agent_network.py` to start an interactive agent network built with LangGraph.

3. **LangGraph Collaborative Project**
   Run `python langgraph_collaborative_task.py` to start a collaborative project simulation with LangGraph agents.
