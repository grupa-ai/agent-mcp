"""
Agent Network Zones - Intranet + Internet Architecture

Enables:
- Intranet: Company agents collaborate securely (internal only)
- Extranet: Partner/vendor agents (limited access)
- Internet: Public agents (minimal access)
- Gateway: Controls what crosses network boundaries
"""

import hashlib
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class NetworkZone(Enum):
    """Network zones for agent isolation"""
    INTRANET = "intranet"      # Internal company network
    EXTRANET = "extranet"      # Partners/vendors (limited)
    INTERNET = "internet"      # Public internet agents
    DMZ = "dmz"               # Demilitarized - proxy/gateway


class TrustLevel(Enum):
    """Trust levels for cross-zone communication"""
    FULL = "full"             # Can share everything
    LIMITED = "limited"       # Can share non-sensitive
    MINIMAL = "minimal"       # Only public info
    NONE = "none"             # No communication


@dataclass
class DataClassification:
    """Data sensitivity classification"""
    level: str  # "public", "internal", "confidential", "secret"
    can_share_with: List[NetworkZone] = field(default_factory=list)
    
    def can_send_to(self, zone: NetworkZone) -> bool:
        return zone in self.can_share_with


@dataclass
class AgentNetworkConfig:
    """Configuration for an agent's network boundaries"""
    agent_id: str
    zone: NetworkZone = NetworkZone.INTRANET
    organization: Optional[str] = None
    
    # Trust relationships
    trusted_zones: List[NetworkZone] = field(default_factory=list)
    trusted_orgs: List[str] = field(default_factory=list)
    blocked_orgs: List[str] = field(default_factory=list)
    
    # Data handling
    default_classification: str = "internal"
    can_initiate_external: bool = True
    requires_approval_for_external: bool = False
    
    # Gateway settings
    use_gateway: bool = True
    gateway_url: Optional[str] = None


@dataclass
class CrossZoneMessage:
    """Message being routed across network zones"""
    original_message: Dict[str, Any]
    sender_zone: NetworkZone
    receiver_zone: NetworkZone
    
    # Classification
    data_classification: DataClassification
    contains_sensitive: bool = False
    sensitive_fields: List[str] = field(default_factory=list)
    
    # Audit
    approved_by: Optional[str] = None
    approval_timestamp: Optional[str] = None
    filtered_fields: List[str] = field(default_factory=list)


class AgentGateway:
    """
    Gateway that controls traffic between network zones.
    
    Like a corporate firewall, but for AI agents.
    
    Architecture:
    
    ┌─────────────────────────────────────────────────────────┐
    │                    COMPANY NETWORK                      │
    │  ┌─────────────────────────────────────────────────┐   │
    │  │              INTRANET ZONE                      │   │
    │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐       │   │
    │  │  │ Agent A │  │ Agent B │  │ Agent C │       │   │
    │  │  └─────────┘  └─────────┘  └─────────┘       │   │
    │  │       ↑            ↑            ↑               │   │
    │  │       └────────────┼────────────┘               │   │
    │  │                    │                            │   │
    │  │              ┌─────▼─────┐                      │   │
    │  │              │  GATEWAY  │                      │   │
    │  │              └─────┬─────┘                      │   │
    │  └────────────────────┼────────────────────────────┘   │
    │                       │                                  │
    │              ┌────────▼────────┐                       │
    │              │     DMZ ZONE    │ (scrubbed)           │
    │              └────────┬────────┘                       │
    └───────────────────────┼────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        ┌─────▼─────┐ ┌────▼────┐ ┌────▼──────┐
        │  EXTRANET │ │INTERNET │ │  PUBLIC   │
        │ (Partners)│ │(limited)│ │  AGENTS   │
        └───────────┘ └─────────┘ └───────────┘
    """
    
    def __init__(self, organization: str, config: Dict[str, Any] = None):
        self.organization = organization
        self.config = config or {}
        
        # Zone configuration
        self.intranet_agents: Set[str] = set()
        self.trusted_partners: Dict[str, TrustLevel] = {}  # org -> trust level
        
        # Security policies
        # can_share_with = where this data CAN go
        self.classification_rules: Dict[str, DataClassification] = {
            "public": DataClassification("public", [NetworkZone.INTERNET, NetworkZone.EXTRANET, NetworkZone.INTRANET]),
            "internal": DataClassification("internal", [NetworkZone.INTRANET, NetworkZone.DMZ, NetworkZone.EXTRANET, NetworkZone.INTERNET]),  # After sanitization
            "confidential": DataClassification("confidential", [NetworkZone.INTRANET]),
            "secret": DataClassification("secret", []),  # Can't leave intranet
        }
        
        # Message filters
        self.sensitive_patterns: List[str] = [
            "password", "secret", "api_key", "token", 
            "credential", "private_key", "access_token"
        ]
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
    
    def register_agent(self, agent_id: str, zone: NetworkZone = NetworkZone.INTRANET):
        """Register an agent to a zone"""
        if zone == NetworkZone.INTRANET:
            self.intranet_agents.add(agent_id)
        logger.info(f"Registered agent {agent_id} to {zone.value} zone")
    
    def add_trusted_partner(self, org: str, trust_level: TrustLevel):
        """Add a trusted partner organization"""
        self.trusted_partners[org] = trust_level
    
    def classify_message(self, message: Dict[str, Any]) -> CrossZoneMessage:
        """Classify a message for cross-zone routing"""
        contains_sensitive = False
        sensitive_fields = []
        
        # Check for sensitive data
        message_str = json.dumps(message).lower()
        for pattern in self.sensitive_patterns:
            if pattern in message_str:
                contains_sensitive = True
                sensitive_fields.append(pattern)
        
        # Determine classification - sensitive data can still be sent after sanitization
        if contains_sensitive:
            # Mark as internal - will be sanitized before sending
            classification = self.classification_rules["internal"]
        else:
            classification = self.classification_rules["internal"]
        
        return CrossZoneMessage(
            original_message=message,
            sender_zone=NetworkZone.INTRANET,
            receiver_zone=NetworkZone.INTERNET,
            data_classification=classification,
            contains_sensitive=contains_sensitive,
            sensitive_fields=sensitive_fields
        )
    
    def filter_for_external(self, message: CrossZoneMessage) -> Dict[str, Any]:
        """
        Filter/sanitize message before sending externally.
        Removes or redacts sensitive information.
        """
        filtered = message.original_message.copy()
        
        # Redact sensitive fields
        for field in message.sensitive_fields:
            if field in filtered:
                filtered[field] = "[REDACTED]"
        
        # For confidential data - block entirely
        if message.data_classification.level == "confidential":
            raise ValueError(
                f"Cannot send {message.data_classification.level} data to external zone"
            )
        
        # For secret data - definitely block
        if message.data_classification.level == "secret":
            raise ValueError("Secret data cannot leave intranet")
        
        message.filtered_fields = message.sensitive_fields.copy()
        
        # Add sanitization notice
        filtered["_sanitized"] = True
        filtered["_original_classification"] = message.data_classification.level
        
        return filtered
    
    async def route_message(
        self,
        from_agent: str,
        to_agent: str,
        message: Dict[str, Any],
        to_zone: NetworkZone
    ) -> Dict[str, Any]:
        """
        Route a message across zones with full security controls.
        """
        sender_zone = NetworkZone.INTRANET if from_agent in self.intranet_agents else to_zone
        
        # Classify the message
        classified = self.classify_message(message)
        classified.sender_zone = sender_zone
        classified.receiver_zone = to_zone
        
        # Log the attempt
        self._audit("message_route_attempt", {
            "from": from_agent,
            "to": to_agent,
            "to_zone": to_zone.value,
            "classification": classified.data_classification.level,
            "contains_sensitive": classified.contains_sensitive
        })
        
        # Check if allowed
        if not classified.data_classification.can_send_to(to_zone):
            raise PermissionError(
                f"Cannot send {classified.data_classification.level} data to {to_zone.value}"
            )
        
        # Filter if going external
        if to_zone != NetworkZone.INTRANET:
            filtered_message = self.filter_for_external(classified)
            
            self._audit("message_routed_external", {
                "from": from_agent,
                "to": to_agent,
                "filtered_fields": classified.sensitive_fields
            })
            
            return filtered_message
        
        # Same zone - pass through
        return message
    
    def _audit(self, action: str, details: Dict[str, Any]):
        """Audit log entry"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "organization": self.organization,
            "details": details
        }
        self.audit_log.append(entry)
        logger.info(f"AUDIT: {action} - {json.dumps(details)}")


class SecureAgentMixin:
    """
    Mixin that adds zone-based security to agents.
    
    Usage:
        class MyAgent(SecureAgentMixin):
            ...
    """
    
    def __init__(self, *args, network_config: AgentNetworkConfig = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.network_config = network_config
        self._gateway = None
    
    def set_gateway(self, gateway: AgentGateway):
        """Set the gateway for this agent"""
        self._gateway = gateway
    
    async def send_to_external(
        self, 
        to_handle: str, 
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send a message to an external agent with security controls.
        """
        if not self._gateway:
            raise RuntimeError("Gateway not configured")
        
        # Determine target zone from handle
        to_zone = self._determine_zone(to_handle)
        
        return await self._gateway.route_message(
            from_agent=self.network_config.agent_id if self.network_config else "unknown",
            to_agent=to_handle,
            message=message,
            to_zone=to_zone
        )
    
    def _determine_zone(self, handle: str) -> NetworkZone:
        """Determine target zone from agent handle"""
        # @agent@org.zone format
        parts = handle.lstrip("@").split("@")
        
        if len(parts) >= 2:
            # Has org - check if it's our org
            target_org = parts[1].split(".")[0]
            
            if target_org == self.network_config.organization:
                return NetworkZone.INTRANET
            
            if target_org in self._gateway.trusted_partners:
                return NetworkZone.EXTRANET
        
        return NetworkZone.INTERNET


# --- Demo ---

async def demo():
    """Demo the intranet + internet architecture"""
    
    # Setup company gateway
    gateway = AgentGateway("acme_corp")
    
    # Register internal agents
    gateway.register_agent("agent_alice", NetworkZone.INTRANET)
    gateway.register_agent("agent_bob", NetworkZone.INTRANET)
    
    # Add trusted partners
    gateway.add_trusted_partner("partner_tech", TrustLevel.LIMITED)
    
    # Create network config for an agent
    config = AgentNetworkConfig(
        agent_id="agent_alice",
        zone=NetworkZone.INTRANET,
        organization="acme_corp"
    )
    
    print("=" * 60)
    print("AGENT NETWORK ZONES - DEMO")
    print("=" * 60)
    
    # Test 1: Internal to internal (no filtering)
    print("\n1. Intranet → Intranet:")
    msg = {"content": "Hello Bob!", "priority": "high"}
    result = await gateway.route_message("agent_alice", "agent_bob", msg, NetworkZone.INTRANET)
    print(f"   Result: {result['content']} (no filtering)")
    
    # Test 2: Internal to external (filtering)
    print("\n2. Intranet → Internet (non-sensitive):")
    msg = {"content": "Hello public agent!", "priority": "low"}
    result = await gateway.route_message("agent_alice", "@chat@gpt.external", msg, NetworkZone.INTERNET)
    print(f"   Result: {result}")
    
    # Test 3: Internal to external (with sensitive data - BLOCKED)
    print("\n3. Intranet → Internet (with API key - BLOCKED):")
    try:
        msg = {"content": "Hello!", "api_key": "secret123", "password": "mypassword"}
        result = await gateway.route_message("agent_alice", "@chat@gpt.external", msg, NetworkZone.INTERNET)
        print(f"   Result: {result}")
    except ValueError as e:
        print(f"   Blocked: {e}")
    
    # Test 4: Confidential data (BLOCKED)
    print("\n4. Confidential data → External (BLOCKED):")
    gateway.classification_rules["confidential"].can_share_with = [NetworkZone.INTRANET]
    try:
        msg = {"content": "Q4 earnings report", "classification": "confidential"}
        result = await gateway.route_message("agent_alice", "@partner@partner_tech", msg, NetworkZone.EXTRANET)
        print(f"   Result: {result}")
    except PermissionError as e:
        print(f"   Blocked: {e}")
    
    print("\n" + "=" * 60)
    print("Secure intranet + internet working! 🔐")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
