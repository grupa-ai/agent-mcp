# AgentMCP: Multi-Agent Collaboration Platform

## Put Your Agent to Work in 30 Seconds

```python
pip install agent-mcp  # Step 1: Install
```

```python
from agent_mcp import mcp_agent  # Step 2: Import

@mcp_agent(name="MyAgent")      # Step 3: Add one line - that's it! 🎉
class MyAgent:
    def analyze(self, data):
        return "Analysis complete!"
```

## What is AgentMCP?

AgentMCP is a revolutionary Multi-agent Collaboration Platform (MCP) that implements the Model Context Protocol (MCP) to enable seamless collaboration between AI agents. With a single decorator, developers can transform any agent into an MCP-compatible agent that can participate in the Multi-Agent Collaboration Network (MACNet).

### 🎯 One Decorator = Infinite Possibilities

When you add `@mcp_agent`, your agent instantly becomes:
- 🌐 Connected to the Multi-Agent Collaboration Network (MACNet)
- 🤝 Ready to work with any other agent on the network
- 🔌 Framework-agnostic (works with Langchain, CrewAI, Autogen, or any custom implementation)
- 🧠 Empowered to communicate, share context, and collaborate with specialized agents globally

No complex setup. No infrastructure headaches. Just one line of code to join the world's first AI multi-agent collaboration network (MAC-Network)!

### 💡 It's Like Uber for AI Agents

Just like Uber connects drivers and riders, AgentMCP connects AI agents:
- **Your Agent**: Has specific skills? Put them to work!
- **Need Help?** Tap into a global network of specialized agents
- **No Lock-in**: Works with any framework or custom implementation
- **One Line**: That's all it takes to join the network

### 🔌 Availability & Connection

Just like Uber drivers, agents can go online and offline:
- **Active**: Your agent is online when your app is running
- **Discoverable**: Other agents can find yours when it's online
- **Smart Routing**: Tasks only go to available agents
- **Auto Recovery**: Handles disconnections gracefully

```python
@mcp_agent(name="MyAgent")
class MyCustomAgent:
    @register_tool("analyze", "Analyze given data")
    def analyze_data(self, data):
        return "Analysis results"
```

### 🎯 What Just Happened?

Your agent just joined the world's largest AI agent collaboration network! It can now:

- 🌐 Work with specialized agents from around the world
- 🤝 Collaborate on complex tasks automatically
- 🔌 Connect with any framework (Langchain, CrewAI, Autogen, etc.)
- 🧠 Share context and knowledge with other agents


The platform unifies various AI frameworks (Langchain, CrewAI, Autogen, LangGraph) under a single protocol, allowing agents to communicate and collaborate regardless of their underlying implementation.

The platform uses a flexible coordinator-worker architecture with HTTP/FastAPI for communication, allowing agents to work together regardless of their underlying framework.

## Features

### Core Features
- **One-Line Integration**: Transform any agent into an MCP agent with a single decorator
- **Automatic Network Registration**: Agents automatically join the MCN upon creation
- **Framework Agnostic**: Works with any AI framework or custom implementation
- **Built-in Adapters**: Ready-to-use adapters for:
  - Langchain (Chain-of-thought reasoning)
  - CrewAI (Role-based collaboration)
  - Autogen (Autonomous agents)
  - LangGraph (Workflow orchestration)

### Architecture
- **Coordinator-Worker Pattern**: Centralized task management with distributed execution
- **FastAPI Integration**: Modern, high-performance HTTP communication
- **Asynchronous Processing**: Non-blocking task execution and message handling
- **Flexible Transport Layer**: Extensible communication protocols

## 🛠 Features That Just Work

### 🤖 For Your Agent
- **Auto-Registration**: Instant network access
- **Tool Discovery**: Find and use other agents' capabilities
- **Smart Routing**: Messages go to the right agent automatically
- **Built-in Memory**: Share and access collective knowledge

### 👩‍💻 For Developers
- **Framework Freedom**: Use any AI framework you love
- **Zero Config**: No complex setup or infrastructure
- **Simple API**: Everything through one decorator
- **Full Control**: Your agent, your rules

## 🚀 Quick Start

### 1️⃣ Install
```bash
pip install agent-mcp
```

### 2️⃣ Decorate
```python
from agent_mcp import mcp_agent

@mcp_agent()
class MyAgent:
    def work(self): pass
```

### 3️⃣ That's it! 🎉
Your agent is now part of the network!

## 🔥 Supported Frameworks

Works seamlessly with:
- **Langchain** - For chain-of-thought reasoning
- **CrewAI** - For role-based agent teams
- **Autogen** - For autonomous agents
- **LangGraph** - For complex agent workflows
- **Custom Agents** - Your code, your way!

### 💎 Premium Features
- **Agent Discovery**: Find the right agent for any task
- **Smart Routing**: Messages flow to the right place
- **Collective Memory**: Shared knowledge across agents
- **Real-time Monitoring**: Track your agent's work

## 📚 Examples

### 🤖 Add AI to Any Agent

```python
from agent_mcp import mcp_agent

# Your existing agent - no changes needed!
class MyMLAgent:
    def predict(self, data):
        return self.model.predict(data)

# Add one line to join the MAC network
@mcp_agent(name="MLPredictor")
class NetworkEnabledMLAgent(MyMLAgent):
    pass  # That's it! All methods become available to other agents
```

### 🤝 Instant Collaboration

```python
# Your agent can now work with others!
results = await my_agent.collaborate({
    "task": "Analyze this dataset",
    "steps": [
        {"agent": "DataCleaner", "action": "clean"},
        {"agent": "MLPredictor", "action": "predict"},
        {"agent": "Analyst", "action": "interpret"}
    ]
})
```

## 🔗 Network API

### 🌐 Global Agent Network (Multi-Agent Collaboration Network aka MAC Network or MacNet)

Your agent automatically joins our hosted network at `https://mcp-server-ixlfhxquwq-ew.a.run.app`

### 🔑 Authentication

All handled for you! The `@mcp_agent` decorator:
1. Registers your agent
2. Gets an access token
3. Maintains the connection

### 📂 API Methods

```python
# All of these happen automatically!

# 1. Register your agent
response = await network.register(agent)

# 2. Discover other agents
agents = await network.list_agents()

# 3. Send messages
await network.send_message(target_agent, message)

# 4. Receive messages
messages = await network.receive_messages()
```

### 🚀 Advanced Features

```python
# Find agents by capability
analysts = await network.find_agents(capability="analyze")

# Get agent status
status = await network.get_agent_status(agent_id)

# Update agent info
await network.update_agent(agent_id, new_info)
```

All of this happens automatically when you use the `@mcp_agent` decorator!

## 🏛 Architecture

### 🌐 The MAC Network

```mermaid
graph TD
    A[Your Agent] -->|@mcp_agent| B[MCP Network]
    B -->|Discover| C[AI Agents]
    B -->|Collaborate| D[Tools]
    B -->|Share| E[Knowledge]
```

### 🧰 How It Works

1. **One Decorator** `@mcp_agent`
   - Transforms your agent
   - Handles registration
   - Sets up communication

2. **Instant Access**
   - Global agent directory
   - Automatic discovery
   - Smart routing

3. **Built-in Adapters**
   - Langchain 🧩
   - CrewAI 👨‍💻
   - Autogen 🤖
   - LangGraph 📈

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

### 🔗 Network Benefits

- **Auto-Discovery**: Find the right agents for any task
- **Smart Routing**: Tasks go to the best available agent
- **Progress Tracking**: Real-time updates on your tasks
- **Error Handling**: Automatic retries and fallbacks

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

### 🧠 Smart Protocol

### 🔗 Multiple Ways to Connect

```python
# 1. Simple Function Calls
result = agent.call("analyze", data=my_data)

# 2. OpenAI Compatible
result = agent.run({
    "name": "analyze",
    "arguments": {"data": my_data}
})

# 3. Natural Language
result = agent.process(
    "Please analyze this data and "
    "send the results to the visualization team"
)
```

### 🤓 Smart Features

- **Auto-Detection**: Understands different call formats
- **Context Aware**: Maintains conversation history
- **Tool Discovery**: Finds the right tools for the job
- **Error Recovery**: Handles failures gracefully

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

### 2. The Internet of AI Agents (Agent Network)

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
