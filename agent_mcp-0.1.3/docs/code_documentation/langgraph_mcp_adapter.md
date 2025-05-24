# LangGraphMCPAdapter Documentation

## Overview
The `LangGraphMCPAdapter` enables LangGraph agents to work within the Model Context Protocol (MCP) framework. It provides seamless integration between LangGraph tools/agents and other framework agents like Autogen and CrewAI through the MCP transport layer.

## Core Components

### Initialization Parameters
- `name`: Agent identifier
- `tools`: List of LangGraph tools
- `process_message`: Custom message processor
- `transport`: MCP transport layer
- `client_mode`: Client mode flag

### Key Features
1. **LangGraph Integration**
   - Wraps LangGraph tools
   - Creates OpenAI-based agent
   - Manages agent executor

2. **Message Processing**
   - Handles incoming messages
   - Manages task queue
   - Processes tasks asynchronously

3. **Transport Layer**
   - HTTP/FastAPI server
   - Message routing
   - Task coordination

## Core Functionality

### Agent Setup
1. **LangGraph Configuration**
   - Initializes ChatOpenAI
   - Creates agent prompt
   - Sets up tools
   - Configures executor

2. **Server Configuration**
   - FastAPI application
   - Message endpoints
   - Event handling

### Message Handling
1. `process_messages()`
   - Receives transport messages
   - Validates message format
   - Routes to task queue
   - Handles acknowledgments

2. `process_tasks()`
   - Executes LangGraph tasks
   - Manages results
   - Handles errors
   - Sends responses

### Task Execution
1. **Task Processing**
   - Queue management
   - Executor invocation
   - Result handling
   - Error recovery

2. **Response Handling**
   - Result formatting
   - Reply routing
   - Acknowledgment
   - Error reporting

## Best Practices

1. **Configuration**
   - Set appropriate mode
   - Configure transport
   - Initialize tools properly
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
# Create LangGraph tools
tools = [Tool1(), Tool2()]

# Initialize adapter
adapter = LangGraphMCPAdapter(
    name="langgraph_agent",
    tools=tools,
    transport=HTTPTransport(),
    client_mode=True
)

# Connect to MCP network
await adapter.connect_to_server("http://localhost:8000")

# Process messages
await adapter.process_messages()
```

## Security Considerations

1. **Message Security**
   - Validate sources
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