# MCPAgent for AutoGen

## Overview

MCPAgent is a powerful extension to AutoGen's agent architecture that implements the Model Context Protocol (MCP). It enables seamless context sharing, standardized tool usage, and transparent interaction between agents and LLMs.

This implementation allows developers to easily create MCP-capable agents by simply inheriting from the MCPAgent class.

## Features

- **Transparent MCP Implementation**: Extends AutoGen's ConversableAgent with full MCP support
- **Context Management**: Built-in tools for managing, accessing, and sharing context
- **Tool Registration**: Easy registration of functions as MCP-compatible tools
- **Agent Integration**: Register other agents as callable tools
- **Minimal Configuration**: Simple inheritance pattern matching AutoGen's existing patterns

## Installation

```bash
# First, install AutoGen if you haven't already
pip install pyautogen

# Then, just include mcp_agent.py in your project
