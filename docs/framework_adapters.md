# Framework Adapters Documentation

## Overview
The framework adapters in AgentMCP enable seamless integration between different AI agent frameworks. Each adapter translates between the framework-specific formats and the MCP protocol, allowing agents from different frameworks to collaborate effectively.

## Adapter Components

### 1. CrewAI Adapter (CrewAIMCPAdapter)

#### Purpose
Adapts CrewAI agents to work within the MCP ecosystem, enabling role-based collaborative agents to participate in multi-framework tasks.

#### Implementation
```python
class CrewAIMCPAdapter(MCPAgent):
    def __init__(
        self,
        name: str,
        transport: HTTPTransport,
        crewai_agent: CrewAgent,
        client_mode: bool = False
    ):
        """
        Initialize CrewAI adapter.
        
        Args:
            name: Agent name
            transport: Communication transport
            crewai_agent: CrewAI agent instance
            client_mode: Whether to operate as client
        """
```

#### Key Features
- Role-based task execution
- CrewAI-specific tool integration
- Task delegation support
- Collaborative decision making

### 2. Langchain Adapter (LangchainMCPAdapter)

#### Purpose
Enables Langchain agents to participate in the MCP ecosystem, providing access to Langchain's extensive tool ecosystem and chain-of-thought capabilities.

#### Implementation
```python
class LangchainMCPAdapter(MCPAgent):
    def __init__(
        self,
        name: str,
        transport: HTTPTransport,
        langchain_agent: BaseLangchainAgent,
        agent_executor: AgentExecutor,
        client_mode: bool = False
    ):
        """
        Initialize Langchain adapter.
        
        Args:
            name: Agent name
            transport: Communication transport
            langchain_agent: Langchain agent instance
            agent_executor: Agent executor for running tools
            client_mode: Whether to operate as client
        """
```

#### Key Features
- Tool integration
- Chain-of-thought reasoning
- Memory management
- Search capabilities

### 3. LangGraph Adapter (LangGraphMCPAdapter)

#### Purpose
Integrates LangGraph's workflow capabilities into the MCP ecosystem, allowing complex task orchestration and graph-based processing.

#### Implementation
```python
class LangGraphMCPAdapter(MCPAgent):
    def __init__(
        self,
        name: str,
        transport: HTTPTransport,
        tools: List[BaseTool],
        client_mode: bool = False
    ):
        """
        Initialize LangGraph adapter.
        
        Args:
            name: Agent name
            transport: Communication transport
            tools: List of tools to use
            client_mode: Whether to operate as client
        """
```

#### Key Features
- Graph-based workflows
- State management
- Tool execution
- Process orchestration

### 4. Argo Agent Adapter (ArgoAgentMcpAdapter)

#### Purpose
Adapts Argo Agents to work within the MCP ecosystem. (Note: Argo Agent specifics are based on common agent patterns due to limited direct documentation access during development).

#### Implementation
```python
class ArgoAgentMcpAdapter(MCPAgent):
    def __init__(
        self,
        name: str,
        argo_agent: PlaceholderArgoAgent, # Replace with actual ArgoAgent type
        transport: Optional[MCPTransport] = None,
        client_mode: bool = False,
        system_message: str = "I am an Argo agent integrated with MCP.",
        **kwargs
    ):
        """
        Initialize Argo Agent adapter.

        Args:
            name: Agent name
            argo_agent: Argo Agent instance (placeholder used in example)
            transport: Communication transport
            client_mode: Whether to operate as client
            system_message: Default system message for the agent
            **kwargs: Additional arguments for MCPAgent
        """
```

#### Key Features (Assumed)
- Task execution based on Argo Agent capabilities.
- Integration with MCP for message exchange.

### 5. LlamaIndex Adapter (LlamaIndexMcpAdapter)

#### Purpose
Enables LlamaIndex agents (e.g., for RAG, data-augmented generation) to participate in the MCP ecosystem.

#### Implementation
```python
class LlamaIndexMcpAdapter(MCPAgent):
    def __init__(
        self,
        name: str,
        llama_index_agent: PlaceholderLlamaIndexAgent, # Replace with actual LlamaIndexAgent type
        transport: Optional[MCPTransport] = None,
        client_mode: bool = False,
        execution_method_name: str = "chat", # e.g., "chat", "query"
        system_message: str = "I am a LlamaIndex agent integrated with MCP.",
        **kwargs
    ):
        """
        Initialize LlamaIndex adapter.

        Args:
            name: Agent name
            llama_index_agent: LlamaIndex agent instance (placeholder used in example)
            transport: Communication transport
            client_mode: Whether to operate as client
            execution_method_name: The method to call on the LlamaIndex agent (e.g., "chat", "query")
            system_message: Default system message for the agent
            **kwargs: Additional arguments for MCPAgent
        """
```

#### Key Features
- Leverages LlamaIndex's data querying and synthesis capabilities.
- Configurable execution method for flexibility.
- Integration with MCP for receiving tasks and sending results.

## Common Adapter Features

### 1. Message Translation
```python
async def _translate_to_framework(self, message: Dict[str, Any]) -> Any:
    """
    Translate MCP message to framework-specific format.
    
    Args:
        message: MCP format message
        
    Returns:
        Framework-specific format
    """
```

### 2. Result Translation
```python
async def _translate_from_framework(self, result: Any) -> Dict[str, Any]:
    """
    Translate framework result to MCP format.
    
    Args:
        result: Framework-specific result
        
    Returns:
        MCP format result
    """
```

### 3. Tool Management
```python
def register_tool(self, tool: Any):
    """
    Register a tool with the framework adapter.
    
    Args:
        tool: Tool to register
    """
```

## Integration Examples

### 1. CrewAI Integration
```python
from crewai import Agent as CrewAgent
from crewai_mcp_adapter import CrewAIMCPAdapter

# Create CrewAI agent
crew_agent = CrewAgent(
    role="Analyst",
    goal="Analyze data",
    backstory="Expert data analyst"
)

# Create adapter
adapter = CrewAIMCPAdapter(
    name="CrewAnalyst",
    transport=transport,
    crewai_agent=crew_agent
)
```

### 2. Langchain Integration
```python
from langchain.agents import create_openai_tools_agent
from langchain_mcp_adapter import LangchainMCPAdapter

# Create Langchain agent
agent, executor = create_openai_tools_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

# Create adapter
adapter = LangchainMCPAdapter(
    name="LangchainWorker",
    transport=transport,
    langchain_agent=agent,
    agent_executor=executor
)
```

### 3. LangGraph Integration
```python
from langgraph_mcp_adapter import LangGraphMCPAdapter

# Create adapter with tools
adapter = LangGraphMCPAdapter(
    name="GraphProcessor",
    transport=transport,
    tools=tools
)
```

### 4. Argo Agent Integration
```python
from agent_mcp import ArgoAgentMcpAdapter, PlaceholderArgoAgent, HTTPTransport

# Assume transport is configured (e.g., HTTPTransport)
# from agent_mcp.mcp_transport import HTTPTransport
# transport = HTTPTransport(host="http://localhost", port=8004)


# Create placeholder Argo Agent
argo_agent_instance = PlaceholderArgoAgent(name="MyArgoBot")

# Create adapter
argo_adapter = ArgoAgentMcpAdapter(
    name="ArgoMCP",
    argo_agent=argo_agent_instance,
    # transport=transport, # Assign if this adapter runs its own server or for client polling
    client_mode=True # Example: if connecting to a central MCP coordinator
)
```

### 5. LlamaIndex Integration
```python
from agent_mcp import LlamaIndexMcpAdapter, PlaceholderLlamaIndexAgent, HTTPTransport

# Assume transport is configured
# transport = HTTPTransport(host="http://localhost", port=8005)

# Create placeholder LlamaIndex Agent
llama_agent_instance = PlaceholderLlamaIndexAgent(name="MyLlamaBot")

# Create adapter
llama_adapter = LlamaIndexMcpAdapter(
    name="LlamaMCP",
    llama_index_agent=llama_agent_instance,
    # transport=transport,
    client_mode=True,
    execution_method_name="chat" # or "query"
)
```

## Task Processing Flow

### 1. Task Receipt
```python
async def _handle_task(self, message: Dict[str, Any]):
    """
    1. Receive MCP task
    2. Translate to framework format
    3. Execute in framework
    4. Translate result back
    5. Send result via MCP
    """
```

### 2. Framework Execution
```python
async def _execute_in_framework(self, task: Any) -> Any:
    """
    Execute task using framework-specific methods.
    
    Implementation varies by framework:
    - CrewAI: Uses agent.execute()
    - Langchain: Uses executor.run()
    - LangGraph: Uses graph.process()
    """
```

## Best Practices

### 1. Error Handling
```python
try:
    result = await adapter.execute_task(task)
except FrameworkError as e:
    # Handle framework-specific error
    logger.error(f"Framework error: {e}")
except AdapterError as e:
    # Handle adapter-specific error
    logger.error(f"Adapter error: {e}")
```

### 2. Resource Management
```python
# Configure framework-specific resources
adapter.configure_resources({
    "max_tokens": 1000,
    "timeout": 30,
    "memory_limit": "500MB"
})
```

### 3. Monitoring
```python
# Set up monitoring
adapter.configure_monitoring({
    "metrics": ["execution_time", "success_rate"],
    "logging": "detailed",
    "alerts": True
})
```

## Framework-Specific Considerations

### 1. CrewAI
- Handle role-based interactions
- Manage agent collaboration
- Track task delegation

### 2. Langchain
- Manage tool registration
- Handle memory chains
- Process callbacks

### 3. LangGraph
- Manage graph state
- Handle node transitions
- Track workflow progress

## Security and Performance

### Security
1. Validate framework inputs
2. Sanitize outputs
3. Implement rate limiting
4. Monitor resource usage

### Performance
1. Cache common operations
2. Optimize translations
3. Monitor memory usage
4. Track execution times
