# Message Handling Architecture

## Sender Resolution Protocol
1. Direct `message.sender` field (root level)
2. `content.sender` in message content dictionary
3. Parsed JSON sender from `content.text` string
4. Fallback to "Unknown" sender

## Adapter Development Guidelines
- Inherit from `MCPAgent` for core message handling
- Override `_extract_sender()` only for protocol-specific needs
- Use shared validation utilities from `message_validation.py`
