# AgentMCP Quick Start Guide

## Installation

```bash
pip install agent-mcp
```

## Basic Usage

### 1. Create an MCP Agent

```python
from agent_mcp import mcp_agent, register_tool

@mcp_agent(name="MyResearchAgent")
class ResearchAgent:
    def __init__(self):
        self.knowledge_base = {}
    
    @register_tool("research", "Research a given topic")
    def research_topic(self, topic: str) -> str:
        return f"Research results for {topic}"
    
    @register_tool("analyze", "Analyze research data")
    def analyze_data(self, data: dict) -> str:
        return f"Analysis of {data}"
```

### 2. Use in Multi-Agent Network

```python
from agent_mcp import HeterogeneousGroupChat

# Create a group chat
group = HeterogeneousGroupChat()

# Add your agent
researcher = ResearchAgent()
group.add_agent(researcher)

# Define a task with dependencies
task = {
    "steps": [
        {
            "task_id": "research",
            "agent": "MyResearchAgent",
            "description": "Research quantum computing"
        },
        {
            "task_id": "analysis",
            "agent": "MyResearchAgent",
            "description": "Analyze research findings",
            "depends_on": ["research"]
        }
    ]
}

# Submit task and get results
results = await group.submit_task(task)
```

## Advanced Features

### 1. Custom Tool Parameters

```python
@mcp_agent(name="MathAgent")
class MathAgent:
    @register_tool(
        name="add_numbers",
        description="Add two numbers together",
        parameters={
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
        }
    )
    def add(self, a: float, b: float) -> float:
        return a + b
```

### 2. Context Management

```python
@mcp_agent(name="ContextAwareAgent")
class ContextAwareAgent:
    def __init__(self):
        self.context = {}
    
    @register_tool("update_context", "Update agent's context")
    def update_context(self, key: str, value: any):
        self.context[key] = value
        return f"Updated {key} in context"
    
    @register_tool("get_context", "Get value from context")
    def get_context(self, key: str):
        return self.context.get(key, "Not found")
```

### 3. Agent Communication

```python
# Agent A
@mcp_agent(name="AgentA")
class AgentA:
    @register_tool("send_message")
    def send_message(self, target: str, message: str):
        return {"to": target, "content": message}

# Agent B
@mcp_agent(name="AgentB")
class AgentB:
    @register_tool("process_message")
    def process_message(self, message: str):
        return f"Processed: {message}"

# Use in group chat
group = HeterogeneousGroupChat()
a = AgentA()
b = AgentB()
group.add_agent(a)
group.add_agent(b)

# Messages are automatically routed between agents
```

## Integration with AI Frameworks

### 1. Langchain Integration

```python
from langchain.agents import Tool
from agent_mcp import mcp_agent

@mcp_agent(name="LangchainAgent")
class MyLangchainAgent:
    def __init__(self):
        self.tools = [
            Tool(
                name="search",
                func=self.search,
                description="Search for information"
            )
        ]
    
    @register_tool("search")
    def search(self, query: str):
        # Your search implementation
        return f"Results for {query}"
```

### 2. CrewAI Integration

```python
from crewai import Agent
from agent_mcp import mcp_agent

@mcp_agent(name="CrewAgent")
class MyCrewAgent(Agent):
    def __init__(self):
        super().__init__(
            role="Researcher",
            goal="Research topics thoroughly",
            backstory="I am an expert researcher"
        )
```

## Best Practices

1. **Tool Registration**:
   - Give clear, descriptive names to tools
   - Provide detailed descriptions
   - Specify parameter types and descriptions

2. **Error Handling**:
   - Implement proper error handling in tools
   - Return meaningful error messages
   - Use try/except blocks for robust operation

3. **Context Management**:
   - Use context for persistent state
   - Clear context when no longer needed
   - Document context structure

4. **Task Dependencies**:
   - Define clear task dependencies
   - Keep dependency chains manageable
   - Handle dependency failures gracefully

## Next Steps

- Check out the examples in the `examples/` directory
- Read the full documentation
- Join our community for support
