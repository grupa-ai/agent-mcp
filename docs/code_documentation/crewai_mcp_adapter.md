# CrewAIMCPAdapter Documentation

## Overview
The `CrewAIMCPAdapter` enables CrewAI agents to work within the Model Context Protocol (MCP) framework. It provides seamless integration between CrewAI agents and other framework agents through the MCP transport layer.

## Core Components

### Initialization Parameters
- `name`: Agent identifier
- `crewai_agent`: CrewAI agent instance
- `process_message`: Custom message processor
- `transport`: Optional transport layer
- `client_mode`: Client mode flag

### Key Features
1. **CrewAI Integration**
   - Wraps CrewAI agents
   - Manages task execution
   - Handles async operations

2. **Message Processing**
   - Handles incoming messages
   - Manages task queue
   - Processes tasks asynchronously

3. **Transport Layer**
   - FastAPI server integration
   - Message routing
   - Task coordination

## Core Functionality

### Message Handling
1. `process_messages()`
   - Receives transport messages
   - Validates message format
   - Routes to task queue
   - Handles acknowledgments

2. `_handle_message()`
   - HTTP message processing
   - Task queueing
   - Error handling

### Task Processing
1. `process_tasks()`
   - Task queue management
   - CrewAI execution
   - Result handling
   - Error recovery

2. Task Components:
   - Task validation
   - Executor invocation
   - Result formatting
   - Response routing

### Task Execution
1. `execute_task()`
   - CrewAI agent invocation
   - Task processing
   - Result formatting
   - Error handling

## Best Practices

1. **Configuration**
   - Set appropriate mode
   - Configure transport
   - Initialize agents properly
   - Handle connections

2. **Error Handling**
   - Validate messages
   - Handle task failures
   - Manage timeouts
   - Log errors

3. **Resource Management**
   - Clean up connections
   - Manage task queue
   - Handle cancellation
   - Monitor performance

## Usage Example
```python
# Create CrewAI agent
crewai_agent = CrewAgent(...)

# Initialize adapter
adapter = CrewAIMCPAdapter(
    name="crewai_agent",
    crewai_agent=crewai_agent,
    transport=HTTPTransport(),
    client_mode=True
)

# Start processing
await adapter.process_messages()
```

## Security Considerations

1. **Message Security**
   - Validate message sources
   - Sanitize inputs
   - Handle sensitive data

2. **Task Security**
   - Validate permissions
   - Protect resources
   - Monitor execution

3. **Network Security**
   - Secure endpoints
   - Manage connections
   - Handle timeouts