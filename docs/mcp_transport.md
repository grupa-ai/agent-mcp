# MCP Transport Layer Documentation

## Overview
The MCP Transport Layer provides a standardized communication interface for agents in the AgentMCP ecosystem. It implements an HTTP-based protocol for message exchange between agents, supporting both synchronous and asynchronous communication patterns.

## Core Components

### HTTPTransport Class

#### Purpose
Handles HTTP-based communication between agents, providing a reliable message transport mechanism with built-in error handling and retry logic.

#### Configuration
```python
transport = HTTPTransport(
    host="localhost",  # Server hostname
    port=8000,        # Server port
    retry_count=3,    # Number of retries for failed requests
    timeout=30        # Request timeout in seconds
)
```

#### Key Methods

1. **send_message**
```python
async def send_message(self, url: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a message to another agent.
    
    Args:
        url: Target agent's endpoint URL
        message: Dictionary containing the message payload
        
    Returns:
        Response from the target agent
        
    Raises:
        TransportError: If message delivery fails after retries
    """
```

2. **receive_message**
```python
async def receive_message(self) -> Optional[Dict[str, Any]]:
    """
    Receive incoming messages from the message queue.
    
    Returns:
        Message dictionary if available, None if queue is empty
    """
```

3. **get_url**
```python
def get_url(self) -> str:
    """
    Get the full URL for this transport instance.
    
    Returns:
        URL string in format http://host:port
    """
```

### Message Format

#### Standard Message Structure
```json
{
    "type": "message_type",      // Type of message (e.g., "task", "result", "register")
    "sender": "agent_name",      // Name of sending agent
    "timestamp": "ISO-8601",     // Message creation timestamp
    "payload": {                 // Message-specific content
        "key": "value"
    },
    "metadata": {                // Optional metadata
        "priority": 1,
        "retry_count": 0
    }
}
```

#### Message Types

1. **Task Message**
```json
{
    "type": "task",
    "task_id": "unique_id",
    "description": "Task description",
    "previous_result": "Result from previous task",
    "reply_to": "http://coordinator:8000"
}
```

2. **Result Message**
```json
{
    "type": "task_result",
    "task_id": "unique_id",
    "result": "Task execution result",
    "status": "success|error",
    "error": "Error message if status is error"
}
```

3. **Registration Message**
```json
{
    "type": "register",
    "agent_name": "worker_name",
    "agent_url": "http://worker:8001",
    "capabilities": ["capability1", "capability2"]
}
```

### Error Handling

#### Transport Errors
- Connection failures
- Timeout errors
- Invalid response formats
- Server errors

#### Retry Mechanism
```python
async def _send_with_retry(self, url: str, message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send message with automatic retries on failure.
    
    Implementation:
    1. Attempt to send message
    2. On failure, wait with exponential backoff
    3. Retry up to configured retry_count
    4. Raise TransportError if all retries fail
    """
```

### Best Practices

1. **Error Handling**
```python
try:
    response = await transport.send_message(url, message)
except TransportError as e:
    # Handle communication failure
    logger.error(f"Failed to send message: {e}")
```

2. **Message Validation**
```python
def validate_message(message: Dict[str, Any]) -> bool:
    """
    Validate message format before sending.
    
    Required fields:
    - type
    - sender
    - timestamp
    - payload
    """
```

3. **URL Management**
```python
# Correct
url = transport.get_url()  # Returns http://host:port

# Incorrect
url = f"http://{transport.host}:{transport.port}"  # Don't construct manually
```

## Integration Examples

### Basic Usage
```python
# Initialize transport
transport = HTTPTransport(host="localhost", port=8000)

# Send message
response = await transport.send_message(
    "http://worker:8001",
    {
        "type": "task",
        "task_id": "123",
        "description": "Process data"
    }
)

# Receive message
message = await transport.receive_message()
if message:
    # Process message
    pass
```

### With FastAPI Integration
```python
from fastapi import FastAPI
app = FastAPI()

@app.post("/message")
async def handle_message(request: Request):
    message = await request.json()
    # Process message
    return {"status": "ok"}
```

## Security Considerations

1. **Network Security**
- Use HTTPS in production
- Implement authentication
- Validate message origins
- Rate limiting

2. **Data Validation**
- Validate all incoming messages
- Sanitize data before processing
- Check message size limits

3. **Error Handling**
- Don't expose internal errors
- Log security-relevant events
- Implement timeout policies
