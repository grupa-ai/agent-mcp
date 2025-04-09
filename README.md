# AgentMCP: The Universal System for AI Agent Collaboration

> Unleashing a new era of AI collaboration: AgentMCP is the system that makes any AI agent work with every other agent - handling all the networking, communication, and coordination between them. Together with MACNet (The Internet of AI Agents), we're creating a world where AI agents can seamlessly collaborate across any framework, protocol, or location.

## Transform Your Agent into a Global Network Participant in 30 Seconds

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

AgentMCP is the world's first universal system for AI agent collaboration. Just as operating systems and networking protocols enabled the Internet, AgentMCP handles all the complex work needed to make AI agents work together:
- Converting agents to speak a common language
- Managing network connections and discovery
- Coordinating tasks and communication
- Ensuring secure and reliable collaboration

With a single decorator, developers can connect their agents to MACNet (our Internet of AI Agents), and AgentMCP takes care of everything else - the networking, translation, coordination, and collaboration. No matter what framework or protocol your agent uses, AgentMCP makes it instantly compatible with our global network of AI agents.

### Why AgentMCP Matters

In today's fragmented AI landscape, agents are isolated by their frameworks and platforms. AgentMCP changes this by:
- **Universal System**: The operating system for AI agent collaboration
- **Global Network**: Connect to MACNet - the Internet of AI Agents
- **Zero Learning Curve**: Transform your agent into a collaborative powerhouse with just one decorator
- **Framework Independence**: Build your agent your way, we handle the collaboration
- **Enterprise Ready**: Scale from prototype to production with enterprise-grade security and management

## Community
Join our Discord community for discussions and support: https://discord.gg/dDTem2P

### 🎯 One Decorator = Infinite Possibilities

> The Power of True Interoperability

When you add `@mcp_agent`, your agent instantly becomes an Agent with MCP App, Client and Server Capabilities :

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

## Supported Frameworks and Protocols

AgentMCP currently supports:
- Autogen
- LangChain
- LangGraph
- CrewAI
- Custom Agents
- A2A Protocol (Coming Soon)

Unlike other solutions that compete with existing frameworks, AgentMCP acts as a universal connector, similar to how the Internet connects different computer networks. We don't replace protocols like A2A - we enable them to work together seamlessly across organizational boundaries.

### Coming Soon
- 🔜 **LlamaIndex**: Planned support
- 🔜 **A2A Protocol**: Future compatibility

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
- 🔌 Connect with any framework (Langchain, CrewAI, Autogen, LangGraph, etc.)
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

## Technical Innovation

### 🔧 Architecture
- **Universal Protocol**: Works with any agent implementation
- **Standard Interface**: Common language for all agents
- **Automatic Discovery**: Agents find the capabilities they need
- **Seamless Handoffs**: Perfect coordination between agents

### 🏢 Enterprise Features
- **Security**: Enterprise-grade authentication and authorization
- **Scalability**: Handle millions of agent interactions
- **Monitoring**: Real-time agent analytics and insights
- **Support**: Enterprise SLA available

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

## Real-World Applications

### 💬 Customer Service
- Route queries to specialized agents
- Maintain context across handoffs
- Scale support operations instantly

### 📈 Data Analysis
- Coordinate multiple analysis agents
- Share insights securely
- Enable parallel processing

### 🔬 Research & Development
- Collaborative information gathering
- Cross-domain expertise
- Automated synthesis

## Roadmap

### Q2 2025
- A2A Protocol Support
- Enhanced security features
- More framework integrations

### Q3 2025
- Enterprise dashboard
- Advanced monitoring
- Custom deployment options

### Q4 2025
- Multi-modal support
- Advanced agent orchestration
- Enterprise features expansion

## Why Choose AgentMCP?

### Comparison with Other Solutions

| Feature | AgentMCP | Traditional Solutions |
|---------|----------|---------------------|
| Setup Time | 30 seconds | Hours/Days |
| Framework Lock-in | None | Usually Required |
| Learning Curve | None | Steep |
| Enterprise Ready | ✅ | Varies |
| Open Source | ✅ | Varies |
| Protocol Standard | MCP & A2A* | Proprietary |
| Community Support | Active | Varies |

*A2A support coming soon

## Get Started Now

1. 💾 Install AgentMCP: `pip install agent-mcp`
2. 🔗 Add one decorator to your agent
3. 🌐 Join the global agent network
4. 🚀 Start collaborating!

[Join our Discord](https://discord.gg/dDTem2P) | [Read the Docs](docs) | [View Examples](examples)

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

Run `python demos/mcp_features_demo.py` to see a step-by-step demonstration of all MCPAgent features:
- Context management operations
- Custom tool registration and usage
- Using agents as tools
- LLM integration with context

This is the best example to start with to understand the core capabilities of MCPAgent.

### 2. The Internet of AI Agents (Agent Network)

Run `python demos/agent_network_example.py` to start an interactive agent network example:
- Simulates a social network of agents
- Each agent has a specialized role (Coordinator, Researcher, Analyst, etc.)
- Agents can communicate with each other through tool calls
- You can interact with any agent and broadcast messages
- Human input is fully supported

This example demonstrates how MCPAgent enables creating complex agent networks where agents can call and interact with each other.

### 3. Collaborative Project

Run `python demos/collaborative_task_example.py` to start a collaborative project simulation:
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
   Run `python demos/langgraph_example.py` to see a step-by-step demonstration of MCPNode with LangGraph.

2. **LangGraph Agent Network**
   Run `python demos/langgraph_agent_network.py` to start an interactive agent network built with LangGraph.

3. **LangGraph Collaborative Project**
   Run `python demos/langgraph_collaborative_task.py` to start a collaborative project simulation with LangGraph agents.
