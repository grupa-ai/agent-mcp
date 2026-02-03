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
python demos/network/test_deployed_network.py
```

### 3. Multi-Provider Cost Optimization (NEW!)

See how AgentMCP automatically reduces costs by 80-90% through intelligent provider selection.

**The Magic:**
- **Automatic Provider Routing**: Chooses most cost-effective AI provider for each task
- **Quality Preservation**: Maintains high quality while reducing costs
- **Real-time Optimization**: Continuously optimizes based on task requirements

*From `demos/cost/test_cost_optimization.py`:*
```python
# Multi-provider setup with cost optimization
providers = [
    {"name": "OpenAI", "model": "gpt-4", "cost_per_token": 0.00003},
    {"name": "Gemini", "model": "gemini-pro", "cost_per_token": 0.00001},
    {"name": "Claude", "model": "claude-3-sonnet", "cost_per_token": 0.000015},
    {"name": "Agent Lightning", "model": "lightning-fast", "cost_per_token": 0.000005}
]

@optimize_costs(target_reduction=0.85)
class MultiProviderAgent:
    def process_task(self, task):
        # Automatically routes to best provider
        return "Task processed at optimal cost!"
```

**What it shows:**
- **80-90% Cost Reduction**: Significant savings without quality loss
- **Provider Flexibility**: Any combination of AI providers supported
- **Transparent Optimization**: See cost breakdown and provider choices

**Run it:**
```bash
python demos/cost/test_cost_optimization.py
```

### 4. Agent Lightning Advanced Features (NEW!)

Experience the revolutionary capabilities of Agent Lightning with Auto-Prompt Optimization (APO) and Reinforcement Learning.

**The Magic:**
- **APO Technology**: Automatically optimizes prompts for better performance
- **Reinforcement Learning**: Agents improve over time through experience
- **Heterogeneous Collaboration**: Works seamlessly with other AI providers

*From `demos/lightning/test_lightning_features.py`:*
```python
@lightning_agent(enable_apo=True, enable_rl=True)
class AdvancedLightningAgent:
    def analyze_data(self, data):
        # APO automatically optimizes the prompt
        # RL improves performance over time
        return self.optimized_analysis(data)
```

**What it shows:**
- **Auto-Prompt Optimization**: 40-60% better results through automatic prompt tuning
- **Reinforcement Learning**: Continuous improvement through experience
- **Seamless Integration**: Works with any other AI framework in AgentMCP

**Run it:**
```bash
python demos/lightning/test_lightning_features.py
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
-   **Multi-Provider Support**: Seamlessly switch between OpenAI, Gemini, Claude, and Agent Lightning.
-   **Cost Optimization**: Automatic 80-90% cost reduction through intelligent routing.
-   **Enterprise Payment Integration**: Built-in Stripe, USDC, and hybrid payment processing.

---

## Supported Frameworks

AgentMCP is designed for broad compatibility:

**Currently Supported:**

-   Autogen
-   LangChain
-   LangGraph
-   CrewAI
-   Custom Agent Implementations
-   ✨ **Agent Lightning** - Revolutionary APO and Reinforcement Learning capabilities
-   ✨ **OpenAI GPT** - Full OpenAI SDK integration
-   ✨ **Google Gemini** - Complete Google AI integration
-   ✨ **Anthropic Claude** - Full Claude API integration
-   ✨ **Multi-Provider Orchestration** - Mix and match any AI providers

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

## 💰 Cost Optimization & Enterprise Features

### 🚀 Revolutionary Cost Savings

AgentMCP now delivers **80-90% cost reduction** through intelligent routing and provider optimization:

```python
# Automatic cost optimization
@optimize_costs(target_reduction=0.85)  # 85% savings target
class MyCostOptimizedAgent:
    def process_data(self, data):
        # Automatically routes to most cost-effective provider
        return "Processing complete at lowest cost!"
```

**How it works:**
- **Intelligent Provider Selection**: Routes tasks to most cost-effective AI provider
- **Model Optimization**: Chooses optimal model sizes for each task
- **Batch Processing**: Groups similar tasks for better pricing
- **Token Optimization**: Minimizes token usage while maintaining quality

### 💳 Enterprise Payment System

Built-in payment gateway supporting multiple payment methods:

```python
# Configure payment processing
payment_config = {
    "provider": "stripe",  # or "usdc" for crypto
    "billing_method": "per_agent",  # Agents use own API keys
    "auto_scaling": True
}
```

**Payment Methods:**
- **Stripe**: Credit card processing
- **USDC**: Cryptocurrency payments
- **Hybrid**: Split payments across methods
- **Per-Agent Billing**: Each agent uses own API keys for security

### 🔐 Zero-Trust Security

Enterprise-grade security with DID-based authentication:
- **Decentralized Identity**: No central authentication server
- **Zero-Trust Architecture**: Every interaction verified
- **Individual Agent Credentials**: Each agent manages own API keys
- **End-to-End Encryption**: All communications encrypted

## 🏛 Architecture

### 🌐 The MAC Network

```mermaid
graph TD
    A[Your Agent] -->|@mcp_agent| B[MCP Network]
    B -->|Discover| C[AI Agents]
    B -->|Collaborate| D[Tools]
    B -->|Share| E[Knowledge]
    B -->|Optimize| F[Cost Management]
    B -->|Process| G[Payment Gateway]
```

### 3️⃣ Run Your App
Your agent automatically connects when your application starts.

## Community
Join our Discord community for discussions, support, and collaboration: [https://discord.gg/dDTem2P](https://discord.gg/dDTem2P)

## Contributing
Contributions are welcome! Please refer to the CONTRIBUTING.md file for guidelines.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
