"""
OpenAPI Protocol Support for AgentMCP
REST API discovery and standardization for agent tools

This module provides OpenAPI 3.0 specification generation and handling,
enabling agents to expose their capabilities through standard REST APIs.
"""

import json
import uuid
import inspect
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class OpenAPIInfo:
    """OpenAPI info object"""
    title: str
    version: str
    description: str
    contact: Dict[str, Any] = None
    license: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.contact is None:
            self.contact = {}
        if self.license is None:
            self.license = {}

@dataclass
class OpenAPIPath:
    """OpenAPI path object"""
    path: str
    method: str
    operation_id: str
    summary: str
    description: str
    parameters: List[Dict[str, Any]] = None
    responses: Dict[str, Any] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.responses is None:
            self.responses = {}
        if self.tags is None:
            self.tags = []

@dataclass
class OpenAPISchema:
    """OpenAPI schema definition"""
    type: str
    properties: Dict[str, Any] = None
    required: List[str] = None
    items: Dict[str, Any] = None
    description: str = ""
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}
        if self.required is None:
            self.required = []
        if self.items is None:
            self.items = {}

class OpenAPIGenerator:
    """Generate OpenAPI 3.0 specifications from agent capabilities"""
    
    def __init__(self, agent_name: str, agent_description: str = ""):
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.paths = []
        self.schemas = {}
        self.tags = []
    
    def add_tool_from_function(
        self,
        func: Callable,
        path: str = None,
        method: str = "POST",
        tags: List[str] = None
    ):
        """Add a tool as an OpenAPI path"""
        try:
            # Get function signature
            sig = inspect.signature(func)
            func_name = func.__name__
            
            # Generate path if not provided
            if not path:
                path = f"/{func_name}"
            
            # Extract parameters from function signature
            parameters = []
            required_params = []
            
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'ctx'):
                    continue
                
                param_info = self._analyze_parameter(param_name, param)
                parameters.append(param_info)
                
                if param.default == inspect.Parameter.empty:
                    required_params.append(param_name)
            
            # Create schema for request body
            request_schema = None
            if method.upper() in ['POST', 'PUT', 'PATCH'] and parameters:
                request_schema = OpenAPISchema(
                    type="object",
                    properties={p["name"]: p["schema"] for p in parameters},
                    required=required_params,
                    description=f"Request body for {func_name}"
                )
            
            # Create response schemas
            responses = {
                "200": {
                    "description": f"Successful response from {func_name}",
                    "content": {
                        "application/json": {
                            "schema": self._create_response_schema(func)
                        }
                    }
                }
            }
            
            # Add error responses
            responses.update({
                "400": {"description": "Bad request - invalid parameters"},
                "500": {"description": "Internal server error"}
            })
            
            # Convert parameters to OpenAPI format
            openapi_params = []
            for param in parameters:
                openapi_param = {
                    "name": param["name"],
                    "in": "body" if method.upper() in ['POST', 'PUT', 'PATCH'] else "query",
                    "description": param["description"],
                    "required": param["required"],
                    "schema": param["schema"]
                }
                openapi_params.append(openapi_param)
            
            # Create path object
            path_obj = OpenAPIPath(
                path=path,
                method=method.upper(),
                operation_id=func_name,
                summary=self._get_function_summary(func),
                description=func.__doc__ or f"Execute {func_name}",
                parameters=openapi_params,
                responses=responses,
                tags=tags or ["tools"]
            )
            
            self.paths.append(path_obj)
            
            # Store schema for request body
            if request_schema:
                self.schemas[f"{func_name}Request"] = request_schema
            
            logger.info(f"Added OpenAPI path: {method} {path}")
            
        except Exception as e:
            logger.error(f"Error adding tool {func.__name__} to OpenAPI: {e}")
    
    def add_mcp_tools_as_paths(self, mcp_tools: Dict[str, Any]):
        """Add MCP tools as OpenAPI paths"""
        for tool_name, tool_info in mcp_tools.items():
            # Create a wrapper function for the tool
            def tool_wrapper(**kwargs):
                return {"tool": tool_name, "args": kwargs}
            
            # Add as OpenAPI path
            self.add_tool_from_function(
                func=tool_wrapper,
                path=f"/tools/{tool_name}",
                method="POST",
                tags=["mcp", "tools"]
            )
    
    def add_agent_info_paths(self, agent_id: str, agent_info: Dict[str, Any]):
        """Add standard agent information paths"""
        
        # GET /agent/info
        def get_agent_info():
            return {
                "agent_id": agent_id,
                "name": agent_info.get("name", agent_id),
                "description": agent_info.get("description", ""),
                "framework": agent_info.get("framework", "unknown"),
                "capabilities": agent_info.get("capabilities", []),
                "status": "active"
            }
        
        self.add_tool_from_function(
            func=get_agent_info,
            path="/agent/info",
            method="GET",
            tags=["agent"]
        )
        
        # GET /agent/health
        def get_agent_health():
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id
            }
        
        self.add_tool_from_function(
            func=get_agent_health,
            path="/agent/health",
            method="GET",
            tags=["agent", "health"]
        )
        
        # GET /agent/capabilities
        def get_agent_capabilities():
            return {
                "agent_id": agent_id,
                "capabilities": agent_info.get("capabilities", []),
                "tools": list(self.schemas.keys())
            }
        
        self.add_tool_from_function(
            func=get_agent_capabilities,
            path="/agent/capabilities",
            method="GET",
            tags=["agent", "capabilities"]
        )
    
    def _analyze_parameter(self, param_name: str, param) -> Dict[str, Any]:
        """Analyze a function parameter and create OpenAPI schema"""
        param_type = "string"
        param_format = None
        param_enum = None
        param_description = f"Parameter {param_name}"
        
        # Try to get type from annotation
        if param.annotation != inspect.Parameter.empty:
            annotation_str = str(param.annotation)
            
            if "int" in annotation_str.lower():
                param_type = "integer"
            elif "float" in annotation_str.lower() or "double" in annotation_str.lower():
                param_type = "number"
            elif "bool" in annotation_str.lower():
                param_type = "boolean"
            elif "list" in annotation_str.lower():
                param_type = "array"
                # Try to get item type
                if hasattr(param.annotation, '__args__') and param.annotation.__args__:
                    item_type = str(param.annotation.__args__[0])
                    if "int" in item_type.lower():
                        param_items = {"type": "integer"}
                    elif "str" in item_type.lower():
                        param_items = {"type": "string"}
                    else:
                        param_items = {"type": "string"}
                else:
                    param_items = {"type": "string"}
            elif "dict" in annotation_str.lower():
                param_type = "object"
        
        # Check if parameter has default value
        param_required = param.default == inspect.Parameter.empty
        
        # Create schema
        schema = {
            "type": param_type,
            "description": param_description
        }
        
        if param_format:
            schema["format"] = param_format
        
        if param_enum:
            schema["enum"] = param_enum
        
        if param_type == "array" and 'param_items' in locals():
            schema["items"] = locals()['param_items']
        
        return {
            "name": param_name,
            "description": param_description,
            "required": param_required,
            "type": param_type,
            "schema": schema
        }
    
    def _create_response_schema(self, func: Callable) -> Dict[str, Any]:
        """Create response schema from function return annotation"""
        try:
            sig = inspect.signature(func)
            return_annotation = sig.return_annotation
            
            if return_annotation == inspect.Parameter.empty:
                return {"type": "object"}  # Default to object
            
            annotation_str = str(return_annotation)
            
            if "dict" in annotation_str.lower():
                return {
                    "type": "object",
                    "additionalProperties": True
                }
            elif "list" in annotation_str.lower():
                if hasattr(return_annotation, '__args__') and return_annotation.__args__:
                    item_type = str(return_annotation.__args__[0])
                    if "str" in item_type.lower():
                        return {"type": "array", "items": {"type": "string"}}
                    elif "int" in item_type.lower():
                        return {"type": "array", "items": {"type": "integer"}}
                    else:
                        return {"type": "array", "items": {"type": "object"}}
                else:
                    return {"type": "array", "items": {"type": "object"}}
            elif "str" in annotation_str.lower():
                return {"type": "string"}
            elif "int" in annotation_str.lower():
                return {"type": "integer"}
            elif "bool" in annotation_str.lower():
                return {"type": "boolean"}
            else:
                return {"type": "object"}
                
        except Exception as e:
            logger.error(f"Error creating response schema: {e}")
            return {"type": "object"}
    
    def _get_function_summary(self, func: Callable) -> str:
        """Get a summary for a function"""
        func_name = func.__name__
        
        # Convert snake_case to Title Case
        return ' '.join(word.capitalize() for word in func_name.split('_'))
    
    def generate_openapi_spec(self, servers: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate complete OpenAPI 3.0 specification"""
        
        # Create info object
        info = OpenAPIInfo(
            title=self.agent_name,
            version="1.0.0",
            description=self.agent_description or f"OpenAPI specification for {self.agent_name}",
            contact={
                "name": "AgentMCP",
                "url": "https://github.com/agentmcp"
            },
            license={
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        )
        
        # Group paths by path
        paths = {}
        for path_obj in self.paths:
            if path_obj.path not in paths:
                paths[path_obj.path] = {}
            
            paths[path_obj.path][path_obj.method.lower()] = {
                "operationId": path_obj.operation_id,
                "summary": path_obj.summary,
                "description": path_obj.description,
                "tags": path_obj.tags,
                "parameters": path_obj.parameters,
                "responses": path_obj.responses
            }
        
        # Default servers
        if not servers:
            servers = [
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                }
            ]
        
        # Create tags
        tags_set = set()
        for path_obj in self.paths:
            tags_set.update(path_obj.tags)
        
        tags = [
            {"name": tag, "description": f"Operations related to {tag}"}
            for tag in sorted(list(tags_set))
        ]
        
        # Complete OpenAPI spec
        spec = {
            "openapi": "3.0.0",
            "info": asdict(info),
            "servers": servers,
            "paths": paths,
            "tags": tags,
            "components": {
                "schemas": self.schemas
            }
        }
        
        return spec

class OpenAPIServer:
    """Serve OpenAPI specification and handle requests"""
    
    def __init__(
        self,
        agent_id: str,
        agent_info: Dict[str, Any],
        mcp_tools: Dict[str, Any] = None,
        host: str = "0.0.0.0",
        port: int = 8080
    ):
        self.agent_id = agent_id
        self.agent_info = agent_info
        self.mcp_tools = mcp_tools or {}
        self.host = host
        self.port = port
        
        # Generate OpenAPI spec
        self.generator = OpenAPIGenerator(
            agent_name=agent_info.get("name", agent_id),
            agent_description=agent_info.get("description", "")
        )
        
        # Add agent info paths
        self.generator.add_agent_info_paths(agent_id, agent_info)
        
        # Add MCP tools as paths
        if self.mcp_tools:
            self.generator.add_mcp_tools_as_paths(self.mcp_tools)
        
        # Generate the spec
        self.openapi_spec = self.generator.generate_openapi_spec([
            {"url": f"http://{host}:{port}", "description": "Development server"}
        ])
    
    def get_spec_json(self) -> str:
        """Get OpenAPI specification as JSON"""
        return json.dumps(self.openapi_spec, indent=2)
    
    def get_spec_yaml(self) -> str:
        """Get OpenAPI specification as YAML"""
        try:
            import yaml
            return yaml.dump(self.openapi_spec, default_flow_style=False)
        except ImportError:
            logger.warning("PyYAML not available, returning JSON")
            return self.get_spec_json()
    
    async def handle_openapi_request(
        self,
        method: str,
        path: str,
        query_params: Dict[str, str] = None,
        body: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle a request to the OpenAPI endpoints"""
        try:
            # Normalize path
            if not path.startswith('/'):
                path = '/' + path
            
            # Find matching path in our spec
            path_obj = None
            for p in self.generator.paths:
                if p.path == path:
                    path_obj = p
                    break
            
            if not path_obj:
                return {
                    "error": "Path not found",
                    "status_code": 404
                }
            
            # Check method
            if path_obj.method.lower() != method.lower():
                return {
                    "error": f"Method {method} not allowed for {path}",
                    "status_code": 405
                }
            
            # Execute the operation
            if path == "/agent/info":
                return await self._handle_agent_info()
            elif path == "/agent/health":
                return await self._handle_agent_health()
            elif path == "/agent/capabilities":
                return await self._handle_agent_capabilities()
            elif path.startswith("/tools/") and self.mcp_tools:
                tool_name = path.replace("/tools/", "")
                if tool_name in self.mcp_tools:
                    return await self._handle_tool_call(tool_name, body or query_params or {})
            
            return {
                "error": "Operation not implemented",
                "status_code": 501
            }
            
        except Exception as e:
            logger.error(f"Error handling OpenAPI request: {e}")
            return {
                "error": str(e),
                "status_code": 500
            }
    
    async def _handle_agent_info(self) -> Dict[str, Any]:
        """Handle agent info request"""
        return {
            "agent_id": self.agent_id,
            "name": self.agent_info.get("name", self.agent_id),
            "description": self.agent_info.get("description", ""),
            "framework": self.agent_info.get("framework", "unknown"),
            "capabilities": self.agent_info.get("capabilities", []),
            "tools": list(self.mcp_tools.keys()),
            "openapi_spec": self.openapi_spec,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _handle_agent_health(self) -> Dict[str, Any]:
        """Handle health check request"""
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": self.agent_id,
            "uptime_seconds": 3600,  # Would be calculated in real implementation
            "memory_usage_mb": 128,  # Would be monitored in real implementation
            "cpu_usage_percent": 15.0  # Would be monitored in real implementation
        }
    
    async def _handle_agent_capabilities(self) -> Dict[str, Any]:
        """Handle capabilities request"""
        return {
            "agent_id": self.agent_id,
            "framework": self.agent_info.get("framework", "unknown"),
            "capabilities": self.agent_info.get("capabilities", []),
            "tools": [
                {
                    "name": tool_name,
                    "description": tool_info.get("description", ""),
                    "parameters": tool_info.get("parameters", [])
                }
                for tool_name, tool_info in self.mcp_tools.items()
            ],
            "openapi_endpoints": [
                {
                    "path": path_obj.path,
                    "method": path_obj.method,
                    "operation_id": path_obj.operation_id,
                    "summary": path_obj.summary
                }
                for path_obj in self.generator.paths
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution request"""
        if tool_name not in self.mcp_tools:
            return {
                "error": f"Tool {tool_name} not found",
                "available_tools": list(self.mcp_tools.keys())
            }
        
        tool_info = self.mcp_tools[tool_name]
        tool_func = tool_info.get("function")
        
        if not tool_func:
            return {
                "error": f"Tool {tool_name} has no executable function"
            }
        
        try:
            # Execute the tool
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**arguments)
            else:
                result = tool_func(**arguments)
            
            return {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "tool_name": tool_name,
                "arguments": arguments,
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

# Export classes for easy importing
__all__ = [
    'OpenAPIInfo',
    'OpenAPIPath', 
    'OpenAPISchema',
    'OpenAPIGenerator',
    'OpenAPIServer'
]