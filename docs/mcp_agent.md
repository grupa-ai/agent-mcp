# MCP Agent Documentation

## Overview
The MCP Agent serves as the foundational building block for all agents in the AgentMCP ecosystem. It implements the Model Context Protocol (MCP) and provides core functionality for message handling, task processing, and inter-agent communication.

## Core Components

### MCPAgent Class

#### Purpose
Provides base agent functionality and MCP protocol implementation. All framework-specific adapters inherit from this class.

#### Initialization
```python
agent = MCPAgent(
    name="agent_name",          # Unique agent identifier
    system_message="...",       # Agent's system message
    llm_config=None,           # Optional LLM configuration
    transport=None,            # Optional transport configuration
    client_mode=False          # Whether agent operates in client mode
)
```

### Key Components

1. **Message Processing**
```python
async def process_messages(self):
    """
    Main message processing loop.
    
    - Receives messages from transport layer
    - Routes messages to appropriate handlers
    - Manages message queue
    - Handles errors and retries
    """
```

2. **Task Processing**
```python
async def process_tasks(self):
    """
    Task execution loop.
    
    - Retrieves tasks from queue
    - Executes tasks
    - Handles results and errors
    - Manages task dependencies
    """
```

3. **Context Management**
```python
def update_context(self, key: str, value: Any):
    """
    Update agent's context.
    
    Args:
        key: Context identifier
        value: Context value
    """
```

### Message Handling

#### Message Types

1. **Task Messages**
```python
async def _handle_task(self, message: Dict[str, Any]):
    """
    Process incoming task messages.
    
    Structure:
    {
        "type": "task",
        "task_id": str,
        "description": str,
        "previous_result": Optional[str],
        "reply_to": str
    }
    """
```

2. **Result Messages**
```python
async def _handle_task_result(self, message: Dict[str, Any]):
    """
    Process task result messages.
    
    Structure:
    {
        "type": "task_result",
        "task_id": str,
        "result": Any,
        "status": str
    }
    """
```

3. **Control Messages**
```python
async def _handle_control(self, message: Dict[str, Any]):
    """
    Process control messages.
    
    Types:
    - stop: Stop agent processing
    - pause: Pause processing
    - resume: Resume processing
    """
```

### Task Execution

#### Task Lifecycle
1. Task Receipt
2. Dependency Check
3. Execution
4. Result Processing
5. Result Distribution

```python
async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a task and return results.
    
    Args:
        task: Task specification
        
    Returns:
        Task execution results
        
    Raises:
        TaskExecutionError: If task execution fails
    """
```

### Error Handling

#### Error Types
1. **CommunicationError**
   - Transport failures
   - Network issues
   - Protocol errors

2. **TaskError**
   - Execution failures
   - Invalid task specifications
   - Resource limitations

3. **ContextError**
   - Missing context
   - Invalid context updates
   - Context access errors

#### Error Handling Strategy
```python
async def _handle_error(self, error: Exception, context: Dict[str, Any]):
    """
    Handle various error types.
    
    1. Log error details
    2. Attempt recovery if possible
    3. Notify relevant components
    4. Update agent state
    """
```

## Integration Examples

### Basic Agent Creation
```python
from mcp_agent import MCPAgent
from mcp_transport import HTTPTransport

# Create transport
transport = HTTPTransport(host="localhost", port=8000)

# Create agent
agent = MCPAgent(
    name="BasicAgent",
    system_message="I am a basic MCP agent",
    transport=transport
)

# Start agent
agent.run()
```

### Task Processing
```python
# Define task
task = {
    "task_id": "task_123",
    "description": "Process data",
    "data": {"key": "value"}
}

# Submit task
result = await agent.execute_task(task)

# Process result
print(f"Task result: {result}")
```

### Context Management
```python
# Update context
agent.update_context("preferences", {
    "language": "English",
    "mode": "verbose"
})

# Get context
prefs = agent.get_context("preferences")

# List context
contexts = agent.list_contexts()
```

## Best Practices

### 1. Error Handling
```python
try:
    result = await agent.execute_task(task)
except TaskExecutionError as e:
    # Handle task failure
    logger.error(f"Task failed: {e}")
except CommunicationError as e:
    # Handle communication failure
    logger.error(f"Communication failed: {e}")
```

### 2. Resource Management
```python
# Set resource limits
agent.set_resource_limits({
    "max_tasks": 100,
    "max_memory": "1GB",
    "timeout": 300
})
```

### 3. Logging
```python
# Configure logging
agent.configure_logging({
    "level": "INFO",
    "format": "detailed",
    "output": "file"
})
```

## Security Considerations

### 1. Authentication
- Implement agent authentication
- Validate message sources
- Use secure communication

### 2. Authorization
- Control task execution permissions
- Manage context access
- Restrict agent capabilities

### 3. Data Protection
- Encrypt sensitive data
- Sanitize inputs
- Implement access controls

## Performance Optimization

### 1. Task Queue Management
- Implement priority queuing
- Balance load across agents
- Monitor queue length

### 2. Resource Usage
- Track memory usage
- Monitor CPU utilization
- Implement rate limiting

### 3. Caching
- Cache frequent contexts
- Store common results
- Optimize message routing
