"""
Multi-Language Agent Registry
Enhanced agent discovery and registration system supporting multiple protocols

This module provides a comprehensive registry for:
- Multi-language agent support (Python, JavaScript, Go, Rust, etc.)
- Multiple protocols (MCP, A2A, OpenAPI, REST)
- Health monitoring and lifecycle management
- Capability discovery and matching
- Protocol auto-detection
"""

import asyncio
import json
import uuid
import hashlib
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class AgentProtocol(Enum):
    """Supported agent protocols"""
    MCP = "mcp"
    A2A = "a2a"
    OPENAPI = "openapi"
    REST = "rest"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    GRPC = "grpc"

class AgentStatus(Enum):
    """Agent registration status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"
    DECOMMISSIONED = "decommissioned"

class AgentLanguage(Enum):
    """Programming languages/frameworks"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    UNKNOWN = "unknown"

@dataclass
class AgentRegistration:
    """Comprehensive agent registration information"""
    agent_id: str
    name: str
    description: str
    language: AgentLanguage
    frameworks: List[str]
    protocols: List[AgentProtocol]
    endpoint: str
    webhook_url: Optional[str] = None
    capabilities: List[str] = None
    security_level: str = "medium"
    owner: Optional[str] = None
    version: str = "1.0.0"
    metadata: Dict[str, Any] = None
    
    # Runtime information
    status: AgentStatus = AgentStatus.PENDING
    registered_at: str = None
    last_heartbeat: Optional[str] = None
    health_status: Optional[str] = None
    health_check_url: Optional[str] = None
    
    # Network information
    ip_address: Optional[str] = None
    region: Optional[str] = None
    latency_ms: Optional[float] = None
    
    # Security information
    auth_token: Optional[str] = None
    public_key: Optional[str] = None
    did: Optional[str] = None  # Decentralized Identifier
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.frameworks is None:
            self.frameworks = []
        if self.metadata is None:
            self.metadata = {}
        if self.registered_at is None:
            self.registered_at = datetime.now(timezone.utc).isoformat()

@dataclass
class HealthCheckResult:
    """Health check result for an agent"""
    agent_id: str
    status: str
    response_time_ms: float
    timestamp: str
    error: Optional[str] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

class ProtocolDetector:
    """Auto-detection of agent protocols"""
    
    def __init__(self):
        self.detected_protocols = {}
    
    async def detect_protocols(self, endpoint: str) -> List[AgentProtocol]:
        """Detect which protocols an agent supports"""
        detected = []
        
        async with aiohttp.ClientSession() as session:
            # Try MCP detection
            if await self._detect_mcp(session, endpoint):
                detected.append(AgentProtocol.MCP)
            
            # Try A2A detection
            if await self._detect_a2a(session, endpoint):
                detected.append(AgentProtocol.A2A)
            
            # Try OpenAPI detection
            if await self._detect_openapi(session, endpoint):
                detected.append(AgentProtocol.OPENAPI)
            
            # Default to REST if endpoint responds
            if not detected and await self._detect_rest(session, endpoint):
                detected.append(AgentProtocol.REST)
        
        return detected
    
    async def _detect_mcp(self, session: aiohttp.ClientSession, endpoint: str) -> bool:
        """Detect if endpoint supports MCP"""
        try:
            # Check for MCP endpoint
            async with session.get(f"{endpoint}/.well-known/mcp", timeout=5) as response:
                return response.status == 200
        except:
            try:
                async with session.get(f"{endpoint}/mcp/info", timeout=5) as response:
                    return response.status == 200
            except:
                return False
    
    async def _detect_a2a(self, session: aiohttp.ClientSession, endpoint: str) -> bool:
        """Detect if endpoint supports A2A"""
        try:
            async with session.get(f"{endpoint}/.well-known/agent.json", timeout=5) as response:
                return response.status == 200
        except:
            return False
    
    async def _detect_openapi(self, session: aiohttp.ClientSession, endpoint: str) -> bool:
        """Detect if endpoint supports OpenAPI"""
        try:
            async with session.get(f"{endpoint}/openapi.json", timeout=5) as response:
                return response.status == 200
        except:
            try:
                async with session.get(f"{endpoint}/api/docs", timeout=5) as response:
                    return response.status == 200
            except:
                return False
    
    async def _detect_rest(self, session: aiohttp.ClientSession, endpoint: str) -> bool:
        """Detect if endpoint supports basic REST"""
        try:
            # Simple ping to base endpoint
            async with session.get(endpoint, timeout=5) as response:
                return response.status < 500
        except:
            return False

class HealthMonitor:
    """Health monitoring for registered agents"""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.health_history = {}
        self.monitoring_active = False
        self.check_task = None
    
    async def start_monitoring(self, agents: Dict[str, AgentRegistration]):
        """Start health monitoring for agents"""
        self.agents = agents
        self.monitoring_active = True
        
        if self.check_task:
            self.check_task.cancel()
        
        self.check_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        if self.check_task:
            self.check_task.cancel()
            self.check_task = None
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await self._check_all_agents()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(10)  # Brief pause before retry
    
    async def _check_all_agents(self):
        """Check health of all registered agents"""
        tasks = []
        
        for agent_id, registration in self.agents.items():
            if registration.status == AgentStatus.ACTIVE and registration.health_check_url:
                tasks.append(self._check_agent_health(agent_id, registration))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_agent_health(self, agent_id: str, registration: AgentRegistration) -> HealthCheckResult:
        """Check health of a single agent"""
        start_time = datetime.now(timezone.utc)
        
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=10)
                
                # Use dedicated health check URL or default to agent endpoint
                check_url = registration.health_check_url or f"{registration.endpoint}/health"
                
                async with session.get(check_url, timeout=timeout) as response:
                    end_time = datetime.now(timezone.utc)
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    result = HealthCheckResult(
                        agent_id=agent_id,
                        status="healthy" if response.status == 200 else "unhealthy",
                        response_time_ms=response_time,
                        timestamp=end_time.isoformat(),
                        details={
                            "http_status": response.status,
                            "endpoint": check_url
                        }
                    )
                    
                    if response.status == 200:
                        registration.last_heartbeat = result.timestamp
                        registration.health_status = "healthy"
                    else:
                        registration.health_status = "unhealthy"
                    
                    # Store in history
                    if agent_id not in self.health_history:
                        self.health_history[agent_id] = []
                    
                    self.health_history[agent_id].append(result)
                    
                    # Keep only last 100 results per agent
                    if len(self.health_history[agent_id]) > 100:
                        self.health_history[agent_id] = self.health_history[agent_id][-100:]
                    
                    return result
                    
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            response_time = (end_time - start_time).total_seconds() * 1000
            
            result = HealthCheckResult(
                agent_id=agent_id,
                status="error",
                response_time_ms=response_time,
                timestamp=end_time.isoformat(),
                error=str(e),
                details={"error_type": type(e).__name__}
            )
            
            registration.health_status = "error"
            
            if agent_id not in self.health_history:
                self.health_history[agent_id] = []
            
            self.health_history[agent_id].append(result)
            
            return result

class MultiLanguageAgentRegistry:
    """Enhanced registry for multi-language agents"""
    
    def __init__(
        self,
        storage_backend = None,
        enable_health_monitoring: bool = True,
        health_check_interval: int = 60,
        require_approval: bool = False
    ):
        self.storage = storage_backend  # Could be Firestore, PostgreSQL, etc.
        self.agents = {}
        self.capability_index = {}  # capability -> [agent_ids]
        self.protocol_index = {}    # protocol -> [agent_ids]
        self.language_index = {}    # language -> [agent_ids]
        
        # Components
        self.protocol_detector = ProtocolDetector()
        self.health_monitor = HealthMonitor(health_check_interval)
        self.require_approval = require_approval
        
        # Start health monitoring if enabled
        if enable_health_monitoring:
            asyncio.create_task(self._start_health_monitoring())
    
    async def _start_health_monitoring(self):
        """Start health monitoring after a short delay"""
        await asyncio.sleep(5)  # Wait for initial agents to be registered
        await self.health_monitor.start_monitoring(self.agents)
    
    async def register_agent(
        self,
        registration: AgentRegistration,
        auto_detect_protocols: bool = True
    ) -> Dict[str, Any]:
        """Register a new agent with enhanced capabilities"""
        try:
            # Validate required fields
            if not self._validate_registration(registration):
                return {
                    "status": "error",
                    "message": "Invalid registration data",
                    "errors": self._get_validation_errors(registration)
                }
            
            # Auto-detect protocols if requested
            if auto_detect_protocols and not registration.protocols:
                detected_protocols = await self.protocol_detector.detect_protocols(registration.endpoint)
                registration.protocols = detected_protocols
                logger.info(f"Auto-detected protocols for {registration.agent_id}: {[p.value for p in detected_protocols]}")
            
            # Generate authentication token
            registration.auth_token = self._generate_agent_token(registration)
            
            # Set initial status
            registration.status = AgentStatus.PENDING if self.require_approval else AgentStatus.ACTIVE
            registration.registered_at = datetime.now(timezone.utc).isoformat()
            
            # Store in registry
            self.agents[registration.agent_id] = registration
            
            # Update indexes
            self._update_indexes(registration)
            
            # Store in persistent storage
            await self.storage.write("agent_registrations", asdict(registration))
            
            # Log registration
            logger.info(f"Registered agent: {registration.agent_id} ({registration.language.value})")
            
            # Start health check for new agent
            if registration.health_check_url:
                asyncio.create_task(self._immediate_health_check(registration))
            
            return {
                "status": "success",
                "agent_id": registration.agent_id,
                "auth_token": registration.auth_token,
                "detected_protocols": [p.value for p in registration.protocols],
                "message": "Agent registered successfully"
            }
            
        except Exception as e:
            logger.error(f"Error registering agent {registration.agent_id}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def register_multi_protocol_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        language: Union[str, AgentLanguage],
        endpoint: str,
        capabilities: List[str] = None,
        frameworks: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Register an agent with multiple protocol support"""
        
        # Normalize language
        if isinstance(language, str):
            try:
                language = AgentLanguage(language.lower())
            except ValueError:
                language = AgentLanguage.UNKNOWN
        
        # Create registration
        registration = AgentRegistration(
            agent_id=agent_id,
            name=name,
            description=description,
            language=language,
            frameworks=frameworks or [],
            protocols=[],  # Will be auto-detected
            endpoint=endpoint,
            capabilities=capabilities or [],
            **kwargs
        )
        
        return await self.register_agent(registration, auto_detect_protocols=True)
    
    async def discover_agents(
        self,
        capability: str = None,
        protocol: AgentProtocol = None,
        language: AgentLanguage = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Discover agents based on various criteria"""
        candidates = []
        
        for agent_id, registration in self.agents.items():
            # Skip inactive agents unless requested
            if active_only and registration.status != AgentStatus.ACTIVE:
                continue
            
            # Filter by capability
            if capability and capability not in registration.capabilities:
                continue
            
            # Filter by protocol
            if protocol and protocol not in registration.protocols:
                continue
            
            # Filter by language
            if language and registration.language != language:
                continue
            
            candidates.append({
                "agent_id": agent_id,
                "name": registration.name,
                "description": registration.description,
                "language": registration.language.value,
                "protocols": [p.value for p in registration.protocols],
                "capabilities": registration.capabilities,
                "status": registration.status.value,
                "endpoint": registration.endpoint,
                "health_status": registration.health_status
            })
        
        return candidates
    
    async def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Update agent registration status"""
        if agent_id not in self.agents:
            return {
                "status": "error",
                "message": f"Agent {agent_id} not found"
            }
        
        registration = self.agents[agent_id]
        old_status = registration.status
        registration.status = status
        
        if metadata:
            registration.metadata.update(metadata)
        
        # Update storage
        await self.storage.update(
            "agent_registrations",
            {"agent_id": agent_id},
            {"status": status.value, "metadata": registration.metadata}
        )
        
        logger.info(f"Updated agent {agent_id} status: {old_status.value} -> {status.value}")
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "old_status": old_status.value,
            "new_status": status.value
        }
    
    async def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an agent"""
        registration = self.agents.get(agent_id)
        if not registration:
            return None
        
        # Get health history
        health_history = self.health_monitor.health_history.get(agent_id, [])
        
        return {
            "registration": asdict(registration),
            "health_history": health_history[-10:],  # Last 10 health checks
            "uptime_percentage": self._calculate_uptime(health_history),
            "average_response_time": self._calculate_avg_response_time(health_history)
        }
    
    async def create_agent_webhook(
        self,
        agent_id: str,
        webhook_url: str,
        events: List[str] = None
    ) -> Dict[str, Any]:
        """Create a webhook for agent events"""
        if agent_id not in self.agents:
            return {
                "status": "error",
                "message": "Agent not found"
            }
        
        registration = self.agents[agent_id]
        registration.webhook_url = webhook_url
        
        # Generate webhook secret
        webhook_secret = self._generate_webhook_secret(agent_id)
        
        # Store webhook info
        webhook_info = {
            "agent_id": agent_id,
            "webhook_url": webhook_url,
            "events": events or ["all"],
            "secret": webhook_secret,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.storage.write("agent_webhooks", webhook_info)
        
        return {
            "status": "success",
            "webhook_url": webhook_url,
            "secret": webhook_secret,
            "message": "Webhook created successfully"
        }
    
    async def handle_webhook(self, agent_id: str, payload: Dict[str, Any], signature: str) -> bool:
        """Handle incoming webhook from an agent"""
        try:
            # Verify webhook signature
            if not self._verify_webhook_signature(agent_id, payload, signature):
                logger.warning(f"Invalid webhook signature for agent {agent_id}")
                return False
            
            # Process webhook based on event type
            event_type = payload.get("event")
            
            if event_type == "health.status":
                await self._handle_health_webhook(agent_id, payload)
            elif event_type == "capability.update":
                await self._handle_capability_webhook(agent_id, payload)
            elif event_type == "status.update":
                await self._handle_status_webhook(agent_id, payload)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling webhook for agent {agent_id}: {e}")
            return False
    
    async def _handle_health_webhook(self, agent_id: str, payload: Dict[str, Any]):
        """Handle health status update webhook"""
        if agent_id in self.agents:
            registration = self.agents[agent_id]
            registration.health_status = payload.get("status")
            registration.last_heartbeat = datetime.now(timezone.utc).isoformat()
    
    async def _handle_capability_webhook(self, agent_id: str, payload: Dict[str, Any]):
        """Handle capability update webhook"""
        if agent_id in self.agents:
            registration = self.agents[agent_id]
            old_capabilities = registration.capabilities.copy()
            new_capabilities = payload.get("capabilities", [])
            
            registration.capabilities = new_capabilities
            
            # Update capability index
            self._update_indexes(registration, old_capabilities)
    
    async def _handle_status_webhook(self, agent_id: str, payload: Dict[str, Any]):
        """Handle status update webhook"""
        new_status = payload.get("status")
        if new_status:
            try:
                status_enum = AgentStatus(new_status)
                await self.update_agent_status(agent_id, status_enum)
            except ValueError:
                logger.error(f"Invalid status in webhook: {new_status}")
    
    def _validate_registration(self, registration: AgentRegistration) -> bool:
        """Validate agent registration data"""
        required_fields = ["agent_id", "name", "description", "language", "endpoint"]
        
        for field in required_fields:
            if not getattr(registration, field):
                return False
        
        # Basic format validation
        if not registration.endpoint.startswith(("http://", "https://")):
            return False
        
        return True
    
    def _get_validation_errors(self, registration: AgentRegistration) -> List[str]:
        """Get validation error messages"""
        errors = []
        
        required_fields = ["agent_id", "name", "description", "language", "endpoint"]
        for field in required_fields:
            if not getattr(registration, field):
                errors.append(f"Missing required field: {field}")
        
        if registration.endpoint and not registration.endpoint.startswith(("http://", "https://")):
            errors.append("Invalid endpoint URL format")
        
        return errors
    
    def _generate_agent_token(self, registration: AgentRegistration) -> str:
        """Generate authentication token for agent"""
        data = f"{registration.agent_id}:{registration.endpoint}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _generate_webhook_secret(self, agent_id: str) -> str:
        """Generate webhook secret for an agent"""
        return secrets.token_urlsafe(32)
    
    def _verify_webhook_signature(self, agent_id: str, payload: Dict[str, Any], signature: str) -> bool:
        """Verify webhook signature"""
        # In production, use proper HMAC verification
        # This is a simplified implementation
        expected_data = json.dumps(payload, sort_keys=True)
        expected_signature = hashlib.sha256(f"{expected_data}:{agent_id}".encode()).hexdigest()
        return secrets.compare_digest(signature, expected_signature)
    
    def _update_indexes(self, registration: AgentRegistration, old_capabilities: List[str] = None):
        """Update capability, protocol, and language indexes"""
        agent_id = registration.agent_id
        
        # Update capability index
        if old_capabilities:
            # Remove old capabilities
            for cap in old_capabilities:
                if cap in self.capability_index and agent_id in self.capability_index[cap]:
                    self.capability_index[cap].remove(agent_id)
        
        for cap in registration.capabilities:
            if cap not in self.capability_index:
                self.capability_index[cap] = []
            if agent_id not in self.capability_index[cap]:
                self.capability_index[cap].append(agent_id)
        
        # Update protocol index
        for protocol in registration.protocols:
            if protocol not in self.protocol_index:
                self.protocol_index[protocol] = []
            if agent_id not in self.protocol_index[protocol]:
                self.protocol_index[protocol].append(agent_id)
        
        # Update language index
        language = registration.language
        if language not in self.language_index:
            self.language_index[language] = []
        if agent_id not in self.language_index[language]:
            self.language_index[language].append(agent_id)
    
    async def _immediate_health_check(self, registration: AgentRegistration):
        """Perform immediate health check on newly registered agent"""
        try:
            start_time = datetime.now(timezone.utc)
            
            async with aiohttp.ClientSession() as session:
                check_url = registration.health_check_url or f"{registration.endpoint}/health"
                timeout = aiohttp.ClientTimeout(total=10)
                
                async with session.get(check_url, timeout=timeout) as response:
                    end_time = datetime.now(timezone.utc)
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    registration.health_status = "healthy" if response.status == 200 else "unhealthy"
                    registration.last_heartbeat = end_time.isoformat()
                    registration.latency_ms = response_time
                    
        except Exception as e:
            registration.health_status = "error"
            registration.last_heartbeat = datetime.now(timezone.utc).isoformat()
            logger.error(f"Immediate health check failed for {registration.agent_id}: {e}")
    
    def _calculate_uptime(self, health_history: List[HealthCheckResult]) -> float:
        """Calculate uptime percentage from health history"""
        if not health_history:
            return 0.0
        
        healthy_checks = sum(1 for check in health_history if check.status == "healthy")
        total_checks = len(health_history)
        
        return (healthy_checks / total_checks) * 100 if total_checks > 0 else 0.0
    
    def _calculate_avg_response_time(self, health_history: List[HealthCheckResult]) -> float:
        """Calculate average response time from health history"""
        if not health_history:
            return 0.0
        
        response_times = [check.response_time_ms for check in health_history if check.response_time_ms is not None]
        
        return sum(response_times) / len(response_times) if response_times else 0.0
    
    async def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_agents = len(self.agents)
        active_agents = sum(1 for reg in self.agents.values() if reg.status == AgentStatus.ACTIVE)
        
        language_stats = {}
        for language in AgentLanguage:
            count = sum(1 for reg in self.agents.values() if reg.language == language)
            if count > 0:
                language_stats[language.value] = count
        
        protocol_stats = {}
        for protocol in AgentProtocol:
            count = sum(1 for reg in self.agents.values() if protocol in reg.protocols)
            if count > 0:
                protocol_stats[protocol.value] = count
        
        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "inactive_agents": total_agents - active_agents,
            "language_distribution": language_stats,
            "protocol_distribution": protocol_stats,
            "capabilities_available": list(self.capability_index.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Export classes for easy importing
__all__ = [
    'AgentProtocol',
    'AgentStatus',
    'AgentLanguage',
    'AgentRegistration',
    'HealthCheckResult',
    'ProtocolDetector',
    'HealthMonitor',
    'MultiLanguageAgentRegistry'
]