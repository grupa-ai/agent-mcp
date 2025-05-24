# 1. Message Handling Strategy (2025-04-26)

## Context
Multiple adapters required duplicate sender extraction logic, leading to maintenance challenges and potential inconsistencies.

## Decision
Centralize message processing in base class with:
- Clear resolution order
- JSON parsing safety
- Documentation for contributors

## Future Considerations
- Schema validation using Pydantic
- Middleware for message validation
- Standardized error reporting
