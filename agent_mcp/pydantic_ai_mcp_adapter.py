"""
Pydantic AI MCP Integration
FastAPI-like agent framework with native MCP support

This module provides integration between Pydantic AI agents and the Model Context Protocol,
offering type-safe, production-ready agent capabilities.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Callable, Union, Type
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Try to import Pydantic AI
try:
    from pydantic_ai import Agent, RunContext
    from pydantic_ai.models import OpenAIModel
    # from pydantic_ai.tools import Tool  # Not available in all versions
    from pydantic_ai.mcp import MCPServerTool, FastMCPToolset
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    Agent = None
    RunContext = None
    logger.warning("Pydantic AI not available. Install with: pip install pydantic-ai")

from .mcp_transport import HTTPTransport

@dataclass
class PydanticAIAgentConfig:
    """Configuration for Pydantic AI agent integration"""
    agent_id: str
    name: str
    description: str
    model: str = "openai:gpt-4o"
    model_type: str = "openai"  # "openai", "anthropic", "gemini"
    api_key: str = None
    mcp_server_url: str = "https://mcp-server-ixlfhxquwq-ew.a.run.app"
    enable_type_validation: bool = True
    enable_retry: bool = True
    max_retries: int = 3
    timeout: int = 30
    debug_mode: bool = False

class PydanticAIMCPAgent:
    """Pydantic AI Agent with MCP capabilities"""
    
    def __init__(
        self,
        config: PydanticAIAgentConfig,
        transport: HTTPTransport = None
    ):
        if not PYDANTIC_AI_AVAILABLE:
            raise ImportError("Pydantic AI is not installed. Install with: pip install pydantic-ai")
            
        self.config = config
        self.transport = transport or HTTPTransport.from_url(config.mcp_server_url)
        self.mcp_id = config.agent_id
        self.mcp_version = "0.1.0"
        self.mcp_tools = {}
        
        # Initialize Pydantic AI agent
        self.agent = None
        self._setup_pydantic_agent()
        
        # Register MCP tools
        self._register_default_mcp_tools()
    
    def _setup_pydantic_agent(self):
        """Setup the Pydantic AI agent"""
        try:
            # Configure model based on type
            if self.config.model_type == "openai":
                model = OpenAIModel(
                    model_name=self.config.model.replace("openai:", ""),
                    api_key=self.config.api_key
                )
            else:
                # For other model types, you'd need to configure appropriately
                model = OpenAIModel(
                    model_name="gpt-4o",
                    api_key=self.config.api_key
                )
            
            # Create the Pydantic AI agent
            self.agent = Agent(
                name=self.config.name,
                model=model,
                system_prompt=self.config.description,
                retries=self.config.max_retries if self.config.enable_retry else 0
            )
            
            logger.info(f"Created Pydantic AI agent: {self.config.name}")
            
        except Exception as e:
            logger.error(f"Error setting up Pydantic AI agent: {e}")
    
    def _register_default_mcp_tools(self):
        """Register default MCP tools for Pydantic AI agent"""
        
        # Pydantic AI specific tools
        self._register_pydantic_tools_as_mcp()
        
        # MCP integration tools
        self._register_mcp_integration_tools()
        
        # Agent management tools
        self._register_agent_management_tools()
    
    def _register_pydantic_tools_as_mcp(self):
        """Register Pydantic AI tools as MCP tools"""
        
        # Get tools from the agent if available
        if hasattr(self.agent, 'tools') and self.agent.tools:
            for tool_name, tool in self.agent.tools.items():
                self._register_tool_as_mcp(tool_name, tool)
    
    def _register_tool_as_mcp(self, tool_name: str, tool: Tool):
        """Register a Pydantic AI tool as MCP tool"""
        
        async def pydantic_tool_wrapper(**kwargs):
            """Wrapper to call Pydantic AI tool through MCP"""
            try:
                # Execute the tool with type validation
                if self.config.enable_type_validation:
                    # Pydantic AI handles type validation automatically
                    result = await tool(**kwargs)
                else:
                    result = await tool(**kwargs)
                
                return {
                    "status": "success",
                    "result": result,
                    "tool_name": tool_name,
                    "framework": "pydantic_ai"
                }
            except Exception as e:
                logger.error(f"Error in Pydantic AI tool {tool_name}: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "tool_name": tool_name
                }
        
        # Extract tool metadata
        tool_info = {
            "name": tool_name,
            "description": getattr(tool, 'description', f"Pydantic AI tool {tool_name}"),
            "parameters": self._extract_pydantic_tool_parameters(tool),
            "function": pydantic_tool_wrapper
        }
        
        self.mcp_tools[tool_name] = tool_info
    
    def _extract_pydantic_tool_parameters(self, tool: Tool) -> List[Dict[str, Any]]:
        """Extract parameters from Pydantic AI tool"""
        parameters = []
        
        try:
            # Pydantic AI tools have function signatures we can inspect
            import inspect
            sig = inspect.signature(tool)
            
            for param_name, param in sig.parameters.items():
                if param_name == 'ctx':  # Skip RunContext parameter
                    continue
                    
                parameter = {
                    "name": param_name,
                    "description": f"Parameter {param_name}",
                    "type": "string",  # Default to string
                    "required": param.default == inspect.Parameter.empty
                }
                
                # Try to determine type from annotation
                if param.annotation != inspect.Parameter.empty:
                    type_str = str(param.annotation)
                    if "int" in type_str.lower():
                        parameter["type"] = "number"
                    elif "bool" in type_str.lower():
                        parameter["type"] = "boolean"
                    elif "list" in type_str.lower():
                        parameter["type"] = "array"
                    elif "dict" in type_str.lower():
                        parameter["type"] = "object"
                
                parameters.append(parameter)
                
        except Exception as e:
            logger.error(f"Error extracting parameters from Pydantic AI tool: {e}")
        
        return parameters
    
    def _register_mcp_integration_tools(self):
        """Register MCP-specific integration tools"""
        
        async def connect_to_mcp_server(server_url: str, tools: List[str] = None) -> Dict[str, Any]:
            """Connect to an external MCP server and use its tools"""
            try:
                if FastMCPToolset and MCPServerTool:
                    # Use Pydantic AI's built-in MCP support
                    mcp_toolset = FastMCPToolset(server_url)
                    
                    # Add specific tools if requested
                    if tools:
                        available_tools = []
                        for tool_name in tools:
                            try:
                                tool = MCPServerTool(server_url, tool_name)
                                available_tools.append(tool)
                            except Exception as e:
                                logger.warning(f"Could not load MCP tool {tool_name}: {e}")
                        
                        if available_tools:
                            # Add tools to agent
                            self.agent.tools.update({
                                f"mcp_{tool.name}": tool for tool in available_tools
                            })
                    
                    return {
                        "status": "success",
                        "message": f"Connected to MCP server at {server_url}",
                        "tools_loaded": len(available_tools) if 'available_tools' in locals() else 0
                    }
                else:
                    # Fallback: manual MCP connection
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{server_url}/tools") as response:
                            if response.status == 200:
                                tools_data = await response.json()
                                return {
                                    "status": "success",
                                    "server_url": server_url,
                                    "available_tools": tools_data.get("tools", [])
                                }
                            else:
                                return {
                                    "status": "error",
                                    "message": f"Failed to connect to MCP server: HTTP {response.status}"
                                }
            except Exception as e:
                logger.error(f"Error connecting to MCP server {server_url}: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "server_url": server_url
                }
        
        self.mcp_tools["connect_to_mcp_server"] = {
            "name": "connect_to_mcp_server",
            "description": "Connect to an external MCP server and import its tools",
            "parameters": [
                {
                    "name": "server_url",
                    "description": "URL of the MCP server to connect to",
                    "type": "string",
                    "required": True
                },
                {
                    "name": "tools",
                    "description": "List of specific tools to import (optional)",
                    "type": "array",
                    "required": False
                }
            ],
            "function": connect_to_mcp_server
        }
    
    def _register_agent_management_tools(self):
        """Register agent management and monitoring tools"""
        
        async def get_agent_info() -> Dict[str, Any]:
            """Get information about this Pydantic AI agent"""
            return {
                "status": "success",
                "agent_info": {
                    "id": self.mcp_id,
                    "name": self.config.name,
                    "description": self.config.description,
                    "framework": "Pydantic AI",
                    "model": self.config.model,
                    "type_validation": self.config.enable_type_validation,
                    "retry_enabled": self.config.enable_retry,
                    "max_retries": self.config.max_retries,
                    "mcp_tools": list(self.mcp_tools.keys())
                }
            }
        
        self.mcp_tools["get_agent_info"] = {
            "name": "get_agent_info",
            "description": "Get detailed information about this Pydantic AI agent",
            "parameters": [],
            "function": get_agent_info
        }
        
        async def update_agent_config(
            new_description: str = None,
            enable_type_validation: bool = None,
            max_retries: int = None
        ) -> Dict[str, Any]:
            """Update agent configuration dynamically"""
            try:
                if new_description:
                    self.config.description = new_description
                    # Update agent system prompt
                    self.agent.system_prompt = new_description
                
                if enable_type_validation is not None:
                    self.config.enable_type_validation = enable_type_validation
                
                if max_retries is not None:
                    self.config.max_retries = max_retries
                    self.agent.retries = max_retries
                
                return {
                    "status": "success",
                    "message": "Agent configuration updated",
                    "config": {
                        "description": self.config.description,
                        "type_validation": self.config.enable_type_validation,
                        "max_retries": self.config.max_retries
                    }
                }
            except Exception as e:
                logger.error(f"Error updating agent config: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }
        
        self.mcp_tools["update_agent_config"] = {
            "name": "update_agent_config",
            "description": "Update the configuration of this agent",
            "parameters": [
                {
                    "name": "new_description",
                    "description": "New system description",
                    "type": "string",
                    "required": False
                },
                {
                    "name": "enable_type_validation",
                    "description": "Enable Pydantic type validation",
                    "type": "boolean",
                    "required": False
                },
                {
                    "name": "max_retries",
                    "description": "Maximum number of retries",
                    "type": "number",
                    "required": False
                }
            ],
            "function": update_agent_config
        }
    
    def add_custom_tool(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: List[Dict[str, Any]] = None
    ):
        """Add a custom tool to the Pydantic AI agent"""
        
        # Register with Pydantic AI agent
        if self.agent:
            self.agent.tools[name] = func
        
        # Register as MCP tool
        async def custom_tool_wrapper(**kwargs):
            """Wrapper for custom tool"""
            try:
                result = await func(**kwargs)
                return {
                    "status": "success",
                    "result": result,
                    "tool_name": name,
                    "type": "custom"
                }
            except Exception as e:
                logger.error(f"Error in custom tool {name}: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "tool_name": name
                }
        
        self.mcp_tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or [],
            "function": custom_tool_wrapper
        }
    
    async def run_agent(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Run the Pydantic AI agent with a message"""
        try:
            # Create run context if provided
            run_context = None
            if context:
                run_context = RunContext(
                    deps=context
                )
            
            # Run the agent
            result = await self.agent.run(message, ctx=run_context)
            
            return {
                "status": "success",
                "result": result.data if hasattr(result, 'data') else str(result),
                "message": message,
                "context_used": context is not None,
                "agent_id": self.mcp_id
            }
            
        except Exception as e:
            logger.error(f"Error running Pydantic AI agent: {e}")
            return {
                "status": "error",
                "message": str(e),
                "message_sent": message
            }
    
    async def register_with_mcp_server(self) -> Dict[str, Any]:
        """Register this Pydantic AI agent with MCP server"""
        registration_data = {
            "agent_id": self.mcp_id,
            "info": {
                "name": self.config.name,
                "description": self.config.description,
                "framework": "Pydantic AI",
                "model": self.config.model,
                "capabilities": {
                    "type_validation": self.config.enable_type_validation,
                    "retry_mechanism": self.config.enable_retry,
                    "max_retries": self.config.max_retries,
                    "tools": list(self.mcp_tools.keys())
                },
                "version": self.mcp_version,
                "features": {
                    "type_safe": True,
                    "fastapi_style": True,
                    "production_ready": True,
                    "debug_mode": self.config.debug_mode
                }
            }
        }
        
        return await self.transport.register_agent(self)
    
    async def execute_mcp_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute an MCP tool"""
        if tool_name in self.mcp_tools:
            tool_func = self.mcp_tools[tool_name]["function"]
            return await tool_func(**kwargs)
        else:
            return {
                "status": "error",
                "message": f"Tool {tool_name} not found",
                "available_tools": list(self.mcp_tools.keys())
            }
    
    def get_mcp_tool_info(self) -> Dict[str, Any]:
        """Get information about all available MCP tools"""
        return {
            "agent_id": self.mcp_id,
            "framework": "Pydantic AI",
            "model": self.config.model,
            "tools": [
                {
                    "name": tool_info["name"],
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
                for tool_info in self.mcp_tools.values()
            ],
            "total_tools": len(self.mcp_tools)
        }

class PydanticAIAgentBridge:
    """Bridge for Pydantic AI agent integration with MCP"""
    
    def __init__(self, mcp_server_url: str = "https://mcp-server-ixlfhxquwq-ew.a.run.app"):
        self.mcp_server_url = mcp_server_url
        self.agents = {}
    
    async def create_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        model: str = "openai:gpt-4o",
        api_key: str = None,
        **kwargs
    ) -> PydanticAIMCPAgent:
        """Create and register a Pydantic AI agent"""
        
        config = PydanticAIAgentConfig(
            agent_id=agent_id,
            name=name,
            description=description,
            model=model,
            api_key=api_key,
            mcp_server_url=self.mcp_server_url,
            **kwargs
        )
        
        agent = PydanticAIMCPAgent(config)
        
        # Register with MCP server
        registration_result = await agent.register_with_mcp_server()
        
        if registration_result.get("status") == "registered":
            logger.info(f"Pydantic AI agent {agent_id} registered with MCP server")
            self.agents[agent_id] = agent
        else:
            logger.error(f"Failed to register Pydantic AI agent {agent_id}: {registration_result}")
        
        return agent
    
    async def create_multi_agent_system(
        self,
        agents_config: List[Dict[str, Any]]
    ) -> Dict[str, PydanticAIMCPAgent]:
        """Create a multi-agent system with Pydantic AI"""
        
        agents = {}
        
        for config in agents_config:
            agent = await self.create_agent(**config)
            agents[config.get("agent_id", agent.mcp_id)] = agent
        
        logger.info(f"Created Pydantic AI multi-agent system with {len(agents)} agents")
        return agents
    
    async def setup_agent_collaboration(
        self,
        agent_ids: List[str],
        collaboration_pattern: str = "sequential"
    ) -> Dict[str, Any]:
        """Setup collaboration between Pydantic AI agents"""
        
        agents = {aid: self.agents[aid] for aid in agent_ids if aid in self.agents}
        
        if len(agents) < 2:
            return {
                "status": "error",
                "message": "Need at least 2 agents for collaboration"
            }
        
        # Implement different collaboration patterns
        if collaboration_pattern == "sequential":
            # Agents work in sequence
            async def sequential_collaboration(task: str) -> Dict[str, Any]:
                results = []
                current_input = task
                
                for agent_id, agent in agents.items():
                    result = await agent.run_agent(current_input)
                    results.append({
                        "agent_id": agent_id,
                        "result": result
                    })
                    
                    # Use result as input for next agent
                    if result.get("status") == "success":
                        current_input = result.get("result", "")
                
                return {
                    "status": "success",
                    "collaboration_type": "sequential",
                    "results": results,
                    "final_result": current_input
                }
        
        elif collaboration_pattern == "parallel":
            # Agents work in parallel
            async def parallel_collaboration(task: str) -> Dict[str, Any]:
                tasks = [
                    agent.run_agent(task) 
                    for agent in agents.values()
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                return {
                    "status": "success",
                    "collaboration_type": "parallel",
                    "results": [
                        {
                            "agent_id": agent_id,
                            "result": result
                        }
                        for agent_id, result in zip(agent_ids, results)
                    ]
                }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown collaboration pattern: {collaboration_pattern}"
            }
        
        # Return the collaboration function
        return {
            "status": "success",
            "collaboration_function": locals().get(f"{collaboration_pattern}_collaboration"),
            "agents": list(agents.keys()),
            "pattern": collaboration_pattern
        }

# Export classes for easy importing
__all__ = [
    'PydanticAIAgentConfig',
    'PydanticAIMCPAgent',
    'PydanticAIAgentBridge'
]