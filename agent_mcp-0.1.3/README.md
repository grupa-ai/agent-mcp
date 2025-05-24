# AgentMCP: The Universal System for AI Agent Collaboration

> Unleashing a new era of AI collaboration: AgentMCP is the system that makes any AI agent work with every other agent - handling all the networking, communication, and coordination between them. Together with MACNet (The Internet of AI Agents), we're creating a world where AI agents can seamlessly collaborate across any framework, protocol, or location.

## ✨ The Magic: Transform Your Agent in 30 Seconds

Turn *any* existing AI agent into a globally connected collaborator with just **one line of code**.

```bash
pip install agent-mcp  # Step 1: Install
```

```python
from agent_mcp import mcp_agent  # Step 2: Import

@mcp_agent(mcp_id="MyAgent")      # Step 3: Add this one decorator! 🎉
class MyExistingAgent:
    # ... your agent's existing code ...
    def analyze(self, data):
        return "Analysis complete!"
```

That's it! Your agent is now connected to the Multi-Agent Collaboration Network (MACNet), ready to work with any other agent, regardless of its framework.

➡️ *Jump to [Quick Demos](#-quick-demos-see-agentmcp-in-action) to see it live!* ⬅️

## What is AgentMCP?

AgentMCP is the world's first universal system for AI agent collaboration. Just as operating systems and networking protocols enabled the Internet, AgentMCP handles all the complex work needed to make AI agents work together:
- Converting agents to speak a common language
- Managing network connections and discovery
- Coordinating tasks and communication
- Ensuring secure and reliable collaboration

With a single decorator, developers can connect their agents to MACNet (our Internet of AI Agents), and AgentMCP takes care of everything else - the networking, translation, coordination, and collaboration. No matter what framework or protocol your agent uses, AgentMCP makes it instantly compatible with our global network of AI agents.

## 📚 Examples

**🚀 Quick Demos: See AgentMCP in Action!**

These examples show the core power of AgentMCP. See how easy it is to connect agents and get them collaborating!

### 1. Simple Multi-Agent Chat (Group Chat)

Watch two agents built with *different frameworks* (Autogen and LangGraph) chat seamlessly.

**The Magic:** The `@mcp_agent` decorator instantly connects them.

*From `demos/basic/simple_chat.py`:*
```python
# --- Autogen Agent --- 
@mcp_agent(mcp_id="AutoGen_Alice")
class AutogenAgent(autogen.ConversableAgent):
    # ... agent code ...

# --- LangGraph Agent --- 
@mcp_agent(mcp_id="LangGraph_Bob")
class LangGraphAgent:
    # ... agent code ...
```
**What it shows:**
- Basic agent-to-agent communication across frameworks.
- How `@mcp_agent` instantly connects agents to the network.
- The foundation of collaborative work.

**Run it:**
```bash
python demos/basic/simple_chat.py
```

### 2. Email Agent Task (Networked Task Execution)

See an `EmailAgent` get tasked by another agent over the network to send an email.

**The Magic:**
1.  The `@mcp_agent` decorator makes `EmailAgent` available on the network.
2.  The coordinating agent targets `EmailAgent` by its `mcp_id` within the task definition.

*From `demos/network/email_agent.py`:*
```python
@mcp_agent(mcp_id="EmailAgent")
class EmailAgent(LangGraphMCPAdapter):
    # ... email sending logic ... 
```

*From `demos/network/test_deployed_network.py` (within task definition):*
```python
    # ... other steps ...
    {
        "task_id": "send_report",
        "agent": "EmailAgent", # <-- Target agent by name!
        "description": "Send the research findings via email",
        "content": { ... email details ... },
        "depends_on": ["market_analysis"]
    }
    # ...
```
**What it shows:**
- An agent becoming an MCP participant.
- Joining the MACNet global network.
- Receiving and executing a task (sending an email) via the network.
- How AgentMCP orchestrates real-world collaboration.

**Files Involved:**
- `demos/network/email_agent.py`: The agent performing the work.
- `demos/network/test_deployed_network.py`: The script initiating the task.
- `agent_mcp/heterogeneous_group_chat.py`: The underlying mechanism managing the interaction.

**Run it:**
*Ensure you have set your SMTP environment variables first (see `email_agent.py`).*
```bash
python demos/network/test_deployed_network.py
```

### Why AgentMCP Matters

In today's fragmented AI landscape, agents are isolated by their frameworks and platforms. AgentMCP changes this by providing:
- **A Universal System**: The operating system for AI agent collaboration.
- **The Global Network (MACNet)**: Connect to the Internet of AI Agents.
- **Simplicity**: Achieve powerful collaboration with minimal effort.
- **Framework Independence**: Build agents your way; we handle the integration.
- **Scalability**: Enterprise-ready features for secure, large-scale deployment.

---

## 🔑 Core Concepts & Benefits

AgentMCP is built on a few powerful ideas:

### 🎯 One Decorator = Infinite Possibilities

> The `@mcp_agent` decorator is the heart of AgentMCP's simplicity and power. Adding it instantly transforms your agent:

-   🌐 **Connects** it to the Multi-Agent Collaboration Network (MACNet).
-   🤝 Makes it **discoverable** and ready to collaborate with any other agent on MACNet.
-   🔌 Ensures **compatibility** regardless of its underlying framework (Langchain, CrewAI, Autogen, Custom, etc.).
-   🧠 Empowers it to **share context** and leverage specialized capabilities from agents worldwide.

*Result: No complex setup, no infrastructure headaches – just seamless integration into the global AI agent ecosystem.* 

### 💡 Analogy: Like Uber for AI Agents

Think of AgentMCP as the platform connecting specialized agents, much like Uber connects drivers and riders:

-   **Your Agent**: Offers its unique skills (like a driver with a car).
-   **Need Help?**: Easily tap into a global network of specialized agents (like hailing a ride).
-   **No Lock-in**: Works with any agent framework or custom implementation.
-   **Effortless Connection**: One decorator is all it takes to join or utilize the network.

### 🛠 Features That Just Work

AgentMCP handles the complexities behind the scenes:

**For Your Agent:**

-   **Auto-Registration & Authentication**: Instant, secure network access.
-   **Tool Discovery & Smart Routing**: Automatically find and communicate with the right agents for the task.
-   **Built-in Basic Memory**: Facilitates context sharing between collaborating agents.
-   **Availability Management**: Handles agent online/offline status and ensures tasks are routed to active agents.

**For Developers:**

-   **Framework Freedom**: Use the AI frameworks you know and love.
-   **Zero Config Networking**: Focus on agent logic, not infrastructure.
-   **Simple API**: Primarily interacts through the `@mcp_agent` decorator and task definitions.
-   **Adapters for Popular Frameworks**: Built-in support for Langchain, CrewAI, Autogen, LangGraph simplifies integration.
-   **Asynchronous & Scalable Architecture**: Built on FastAPI for high performance.

---

## Supported Frameworks

AgentMCP is designed for broad compatibility:

**Currently Supported:**

-   Autogen
-   LangChain
-   LangGraph
-   CrewAI
-   Custom Agent Implementations

**Coming Soon:**

-   🔜 LlamaIndex
-   🔜 A2A Protocol Integration

*AgentMCP acts as a universal connector, enabling agents from different ecosystems to work together seamlessly.*

## 🚀 Quick Start (Reference)

For quick reference, here's the basic setup again:

### 1️⃣ Install
```bash
pip install agent-mcp
```

### 2️⃣ Decorate
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

## Network API

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

### 3️⃣ Run Your App
Your agent automatically connects when your application starts.

## Community
Join our Discord community for discussions, support, and collaboration: [https://discord.gg/dDTem2P](https://discord.gg/dDTem2P)

## Contributing
Contributions are welcome! Please refer to the CONTRIBUTING.md file for guidelines.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
