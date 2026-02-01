"""
Microsoft Agent Framework Integration
Combines Semantic Kernel + AutoGen with MCP support

This module provides integration with Microsoft's unified agent framework
that brings together Semantic Kernel and AutoGen capabilities.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Try to import Microsoft frameworks
try:
    import semantic_kernel as sk
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion
    from semantic_kernel.kernel import Kernel
    from semantic_kernel.planning import SequentialPlanner
    from semantic_kernel.skills.core import TimeSkill
    from semantic_kernel.orchestration import SkillContext
    SEMANTIC_KERNEL_AVAILABLE = True
except ImportError:
    SEMANTIC_KERNEL_AVAILABLE = False
    sk = None
    Kernel = None
    logger.warning("Semantic Kernel not available. Install with: pip install semantic-kernel")

try:
    from autogen import ConversableAgent, Agent, GroupChat, GroupChatManager
    AUTOGEN_AVAILABLE = True
except ImportError:
    AUTOGEN_AVAILABLE = False
    ConversableAgent = None
    Agent = None
    logger.warning("AutoGen not available. Install with: pip install pyautogen")

from .mcp_transport import HTTPTransport

@dataclass
class MicrosoftAgentConfig:
    """Configuration for Microsoft Agent Framework integration"""
    agent_id: str
    name: str
    description: str
    framework: str = "unified"  # "semantic_kernel", "autogen", "unified"
    llm_config: Dict[str, Any] = None
    skills: List[str] = None
    mcp_server_url: str = "https://mcp-server-ixlfhxquwq-ew.a.run.app"
    enable_monitoring: bool = True
    enable_compliance: bool = True
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.llm_config is None:
            self.llm_config = {}

class MicrosoftMCPAgent:
    """Microsoft Agent with MCP capabilities"""
    
    def __init__(
        self,
        config: MicrosoftAgentConfig,
        transport: HTTPTransport = None
    ):
        self.config = config
        self.transport = transport or HTTPTransport.from_url(config.mcp_server_url)
        self.mcp_id = config.agent_id
        self.mcp_version = "0.1.0"
        self.mcp_tools = {}
        
        # Initialize Microsoft frameworks
        self.kernel = None
        self.autogen_agent = None
        self.group_chat = None
        
        # Setup based on framework choice
        if config.framework in ["semantic_kernel", "unified"] and SEMANTIC_KERNEL_AVAILABLE:
            self._setup_semantic_kernel()
        
        if config.framework in ["autogen", "unified"] and AUTOGEN_AVAILABLE:
            self._setup_autogen()
        
        # Register MCP tools
        self._register_default_mcp_tools()
    
    def _setup_semantic_kernel(self):
        """Setup Semantic Kernel"""
        try:
            self.kernel = Kernel()
            
            # Add LLM based on config
            llm_config = self.config.llm_config
            if llm_config.get("api_type") == "azure":
                self.kernel.add_chat_service(
                    "azure_openai", 
                    AzureChatCompletion(
                        deployment_name=llm_config.get("deployment_name", "gpt-35-turbo"),
                        endpoint=llm_config.get("endpoint"),
                        api_key=llm_config.get("api_key")
                    )
                )
            else:
                self.kernel.add_chat_service(
                    "openai",
                    OpenAIChatCompletion(
                        ai_model_id=llm_config.get("model", "gpt-3.5-turbo"),
                        api_key=llm_config.get("api_key")
                    )
                )
            
            # Add default skills
            self.kernel.import_skill(TimeSkill(), "TimeSkill")
            
            # Add custom skills from config
            for skill_name in self.config.skills:
                try:
                    # Try to import and add skill
                    skill = self._load_skill(skill_name)
                    if skill:
                        self.kernel.import_skill(skill, skill_name)
                        logger.info(f"Added Semantic Kernel skill: {skill_name}")
                except Exception as e:
                    logger.error(f"Failed to load skill {skill_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error setting up Semantic Kernel: {e}")
    
    def _setup_autogen(self):
        """Setup AutoGen agent"""
        try:
            llm_config = self.config.llm_config
            
            # AutoGen LLM config format
            autogen_config = {
                "model": llm_config.get("model", "gpt-3.5-turbo"),
                "api_key": llm_config.get("api_key"),
                "temperature": llm_config.get("temperature", 0.7)
            }
            
            if llm_config.get("api_type") == "azure":
                autogen_config.update({
                    "base_url": llm_config.get("endpoint"),
                    "api_version": "2023-12-01-preview",
                    "deployment_name": llm_config.get("deployment_name")
                })
            
            self.autogen_agent = ConversableAgent(
                name=self.config.name,
                llm_config=autogen_config,
                system_message=self.config.description,
                human_input_mode="NEVER",
                code_execution_config=False,
                max_consecutive_auto_reply=3
            )
            
            logger.info(f"Created AutoGen agent: {self.config.name}")
            
        except Exception as e:
            logger.error(f"Error setting up AutoGen: {e}")
    
    def _load_skill(self, skill_name: str):
        """Load a Semantic Kernel skill by name"""
        # This is a placeholder for skill loading logic
        # In practice, this would load from various sources
        
        if skill_name == "WebSearch":
            return self._create_web_search_skill()
        elif skill_name == "FileIO":
            return self._create_file_io_skill()
        else:
            return None
    
    def _create_web_search_skill(self):
        """Create a web search skill for Semantic Kernel"""
        @sk.sk_function(description="Search the web for information")
        async def search_web(query: str) -> str:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    # Use a search API (placeholder)
                    url = f"https://api.duckduckgo.com/?q={query}&format=json"
                    async with session.get(url) as response:
                        data = await response.json()
                        results = data.get("AbstractText", "No results found")
                        return str(results)
            except Exception as e:
                return f"Search error: {e}"
        
        return search_web
    
    def _create_file_io_skill(self):
        """Create a file I/O skill for Semantic Kernel"""
        @sk.sk_function(description="Read a file")
        def read_file(file_path: str) -> str:
            try:
                with open(file_path, 'r') as f:
                    return f.read()
            except Exception as e:
                return f"Error reading file: {e}"
        
        return read_file
    
    def _register_default_mcp_tools(self):
        """Register default MCP tools for Microsoft Agent"""
        
        # Semantic Kernel tools
        if self.kernel:
            self._register_kernel_tools_as_mcp()
        
        # AutoGen tools
        if self.autogen_agent:
            self._register_autogen_tools_as_mcp()
        
        # Unified Microsoft tools
        self._register_microsoft_tools_as_mcp()
    
    def _register_kernel_tools_as_mcp(self):
        """Register Semantic Kernel skills as MCP tools"""
        if not self.kernel:
            return
        
        # Register each available skill
        for skill_name, skill in self.kernel.skills.items():
            for function_name, function in skill.items():
                mcp_tool_name = f"sk_{skill_name}_{function_name}"
                
                async def kernel_tool_wrapper(**kwargs):
                    """Wrapper to call Semantic Kernel function"""
                    try:
                        context = SkillContext()
                        result = await function.invoke_async(context=context, **kwargs)
                        return {
                            "status": "success",
                            "result": str(result),
                            "tool_name": mcp_tool_name,
                            "framework": "semantic_kernel"
                        }
                    except Exception as e:
                        logger.error(f"Error in Semantic Kernel tool {mcp_tool_name}: {e}")
                        return {
                            "status": "error",
                            "message": str(e),
                            "tool_name": mcp_tool_name
                        }
                
                self.mcp_tools[mcp_tool_name] = {
                    "name": mcp_tool_name,
                    "description": function.description or f"Semantic Kernel {function_name}",
                    "parameters": self._extract_kernel_function_parameters(function),
                    "function": kernel_tool_wrapper
                }
    
    def _register_autogen_tools_as_mcp(self):
        """Register AutoGen agent capabilities as MCP tools"""
        if not self.autogen_agent:
            return
        
        async def autogen_send_message(message: str, target_agent: str = None) -> Dict[str, Any]:
            """Send a message through AutoGen"""
            try:
                if target_agent:
                    # Send to specific agent
                    response = await self.autogen_agent.a_generate_reply(
                        [{"content": message, "role": "user"}]
                    )
                else:
                    # Internal message processing
                    response = await self.autogen_agent.a_generate_reply(
                        [{"content": message, "role": "user"}]
                    )
                
                return {
                    "status": "success",
                    "result": response,
                    "tool_name": "autogen_send_message",
                    "framework": "autogen"
                }
            except Exception as e:
                logger.error(f"Error in AutoGen tool: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "tool_name": "autogen_send_message"
                }
        
        self.mcp_tools["autogen_send_message"] = {
            "name": "autogen_send_message",
            "description": "Send a message using AutoGen framework",
            "parameters": [
                {
                    "name": "message",
                    "description": "The message to send",
                    "type": "string",
                    "required": True
                },
                {
                    "name": "target_agent",
                    "description": "Optional target agent name",
                    "type": "string",
                    "required": False
                }
            ],
            "function": autogen_send_message
        }
    
    def _register_microsoft_tools_as_mcp(self):
        """Register Microsoft-specific MCP tools"""
        
        async def get_agent_capabilities() -> Dict[str, Any]:
            """Get capabilities of this Microsoft Agent"""
            capabilities = {
                "framework": self.config.framework,
                "semantic_kernel_available": self.kernel is not None,
                "autogen_available": self.autogen_agent is not None,
                "skills": self.config.skills,
                "tools": list(self.mcp_tools.keys())
            }
            return {
                "status": "success",
                "result": capabilities,
                "agent_id": self.mcp_id
            }
        
        self.mcp_tools["get_agent_capabilities"] = {
            "name": "get_agent_capabilities",
            "description": "Get capabilities and configuration of this Microsoft Agent",
            "parameters": [],
            "function": get_agent_capabilities
        }
        
        async def execute_skill(skill_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
            """Execute a Semantic Kernel skill"""
            if not self.kernel:
                return {"status": "error", "message": "Semantic Kernel not available"}
            
            try:
                context = SkillContext()
                skill_function = self.kernel.skills.get_function(skill_name)
                if not skill_function:
                    return {"status": "error", "message": f"Skill {skill_name} not found"}
                
                result = await skill_function.invoke_async(
                    context=context, 
                    **(parameters or {})
                )
                
                return {
                    "status": "success",
                    "result": str(result),
                    "skill_name": skill_name
                }
            except Exception as e:
                logger.error(f"Error executing skill {skill_name}: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "skill_name": skill_name
                }
        
        self.mcp_tools["execute_skill"] = {
            "name": "execute_skill",
            "description": "Execute a Semantic Kernel skill",
            "parameters": [
                {
                    "name": "skill_name",
                    "description": "Name of the skill to execute",
                    "type": "string",
                    "required": True
                },
                {
                    "name": "parameters",
                    "description": "Parameters for the skill",
                    "type": "object",
                    "required": False
                }
            ],
            "function": execute_skill
        }
    
    def _extract_kernel_function_parameters(self, function) -> List[Dict[str, Any]]:
        """Extract parameters from Semantic Kernel function"""
        parameters = []
        
        if hasattr(function, 'parameters') and function.parameters:
            for param_name, param_info in function.parameters.items():
                parameter = {
                    "name": param_name,
                    "description": param_info.description or f"Parameter {param_name}",
                    "type": "string",  # Default to string
                    "required": param_info.default_value is None
                }
                
                # Try to determine type
                if hasattr(param_info, 'type_info'):
                    type_str = str(param_info.type_info)
                    if "int" in type_str.lower():
                        parameter["type"] = "number"
                    elif "bool" in type_str.lower():
                        parameter["type"] = "boolean"
                
                parameters.append(parameter)
        
        return parameters
    
    async def register_with_mcp_server(self) -> Dict[str, Any]:
        """Register this Microsoft Agent with MCP server"""
        registration_data = {
            "agent_id": self.mcp_id,
            "info": {
                "name": self.config.name,
                "description": self.config.description,
                "framework": "Microsoft Agent Framework",
                "framework_type": self.config.framework,
                "capabilities": {
                    "semantic_kernel": self.kernel is not None,
                    "autogen": self.autogen_agent is not None,
                    "skills": self.config.skills,
                    "tools": list(self.mcp_tools.keys())
                },
                "version": self.mcp_version,
                "microsoft_features": {
                    "monitoring": self.config.enable_monitoring,
                    "compliance": self.config.enable_compliance
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
    
    async def create_agent_collaboration(
        self, 
        other_agents: List['MicrosoftMCPAgent'],
        collaboration_type: str = "group_chat"
    ) -> 'AgentGroup':
        """Create collaboration between Microsoft Agents"""
        
        if collaboration_type == "group_chat" and AUTOGEN_AVAILABLE:
            # Create AutoGen group chat
            agents = [self.autogen_agent] + [agent.autogen_agent for agent in other_agents if agent.autogen_agent]
            
            if len(agents) > 1:
                self.group_chat = GroupChat(
                    agents=agents,
                    messages=[],
                    max_round=10
                )
                
                group_manager = GroupChatManager(
                    groupchat=self.group_chat,
                    llm_config=self.config.llm_config
                )
                
                return AgentGroup(
                    type="autogen_group_chat",
                    manager=group_manager,
                    agents=agents
                )
        
        elif collaboration_type == "semantic_kernel_orchestration":
            # Use Semantic Kernel for orchestration
            if self.kernel:
                planner = SequentialPlanner(self.kernel)
                
                async def orchestrate_task(task: str) -> Dict[str, Any]:
                    try:
                        plan = await planner.create_plan_async(task)
                        result = await plan.invoke_async()
                        return {
                            "status": "success",
                            "result": str(result),
                            "plan_steps": len(plan._steps)
                        }
                    except Exception as e:
                        return {
                            "status": "error",
                            "message": str(e)
                        }
                
                return AgentGroup(
                    type="semantic_kernel_orchestration",
                    planner=planner,
                    execute_function=orchestrate_task
                )
        
        return None

@dataclass
class AgentGroup:
    """Represents a group of collaborating agents"""
    type: str
    agents: List[Any] = None
    manager: Any = None
    planner: Any = None
    execute_function: Callable = None

class MicrosoftAgentBridge:
    """Bridge for Microsoft Agent Framework integration with MCP"""
    
    def __init__(self, mcp_server_url: str = "https://mcp-server-ixlfhxquwq-ew.a.run.app"):
        self.mcp_server_url = mcp_server_url
        self.agents = {}
        self.groups = {}
    
    async def create_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        framework: str = "unified",
        llm_config: Dict[str, Any] = None,
        skills: List[str] = None
    ) -> MicrosoftMCPAgent:
        """Create and register a Microsoft Agent"""
        
        config = MicrosoftAgentConfig(
            agent_id=agent_id,
            name=name,
            description=description,
            framework=framework,
            llm_config=llm_config or {},
            skills=skills or [],
            mcp_server_url=self.mcp_server_url
        )
        
        agent = MicrosoftMCPAgent(config)
        
        # Register with MCP server
        registration_result = await agent.register_with_mcp_server()
        
        if registration_result.get("status") == "registered":
            logger.info(f"Microsoft Agent {agent_id} registered with MCP server")
            self.agents[agent_id] = agent
        else:
            logger.error(f"Failed to register Microsoft Agent {agent_id}: {registration_result}")
        
        return agent
    
    async def create_collaboration(
        self,
        agent_ids: List[str],
        collaboration_type: str = "group_chat"
    ) -> Optional[AgentGroup]:
        """Create collaboration between agents"""
        
        agents = [self.agents[aid] for aid in agent_ids if aid in self.agents]
        
        if len(agents) < 2:
            logger.error("Need at least 2 agents for collaboration")
            return None
        
        # Use the first agent to create the group
        lead_agent = agents[0]
        other_agents = agents[1:]
        
        group = await lead_agent.create_agent_collaboration(
            other_agents, collaboration_type
        )
        
        if group:
            group_id = str(uuid.uuid4())
            self.groups[group_id] = group
            logger.info(f"Created {collaboration_type} group with {len(agents)} agents")
        
        return group

# Export classes for easy importing
__all__ = [
    'MicrosoftAgentConfig',
    'MicrosoftMCPAgent',
    'AgentGroup',
    'MicrosoftAgentBridge'
]