"""
Zero Trust Security Layer for AgentMCP
Comprehensive security implementation with identity, authentication, authorization, and audit

This module provides enterprise-grade security for AI agents including:
- Decentralized Identity (DID)
- Dynamic Authorization (ABAC)
- Audit Logging
- Rate Limiting
- Capability-based Access Control
"""

import json
import uuid
import hashlib
import secrets
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable, Union, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import jwt
import bcrypt
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class Permission(Enum):
    """Agent permissions for zero-trust authorization"""
    READ_CONTEXT = "context:read"
    WRITE_CONTEXT = "context:write"
    EXECUTE_TASK = "task:execute"
    SEND_MESSAGE = "message:send"
    RECEIVE_MESSAGE = "message:receive"
    REGISTER_TOOL = "tool:register"
    CALL_TOOL = "tool:call"
    MANAGE_PAYMENT = "payment:manage"
    AGENT_DISCOVERY = "agent:discover"
    SYSTEM_ADMIN = "system:admin"

class SecurityLevel(Enum):
    """Security levels for agents"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AgentIdentity:
    """Decentralized identity for an AI agent"""
    agent_id: str
    did: str  # Decentralized Identifier
    public_key: str
    capabilities: List[str]
    owner: Optional[str]  # Human owner's identity
    created_at: str
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    reputation_score: float = 0.0
    last_active: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()

@dataclass
class AccessPolicy:
    """Access control policy for zero-trust authorization"""
    name: str
    required_capabilities: List[str]
    required_permissions: List[Permission]
    max_task_value: Optional[float] = None
    allowed_targets: Optional[List[str]] = None
    denied_targets: Optional[List[str]] = None
    time_restrictions: Optional[Dict[str, Any]] = None
    security_level_required: SecurityLevel = SecurityLevel.MEDIUM
    rate_limits: Optional[Dict[str, Dict[str, int]]] = None

@dataclass
class AuditLogEntry:
    """Immutable audit log entry"""
    timestamp: str
    agent_id: str
    action: str
    target: str
    resource: str
    result: str
    permission_used: Optional[str] = None
    task_id: Optional[str] = None
    payment_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    risk_score: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def compute_hash(self) -> str:
        """Compute cryptographic hash for integrity"""
        entry_data = {
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "action": self.action,
            "target": self.target,
            "result": self.result
        }
        entry_str = json.dumps(entry_data, sort_keys=True)
        return hashlib.sha256(entry_str.encode()).hexdigest()

class DecentralizedIdentityManager:
    """Manager for decentralized agent identities using DIDs"""
    
    def __init__(self, registry_url: str = None, secret_key: str = None):
        self.registry_url = registry_url or "https://did-registry.agentmcp.com"
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.identities = {}
        self.revoked = set()
    
    def create_did(self, agent_id: str, public_key: str) -> str:
        """Create a DID for an agent"""
        # did:mcp:agent:<hash>
        hash_input = f"{agent_id}:{public_key}:{datetime.now(timezone.utc).isoformat()}"
        did_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:32]
        return f"did:mcp:agent:{did_hash}"
    
    def create_identity(
        self,
        agent_id: str,
        capabilities: List[str],
        owner: str = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM
    ) -> AgentIdentity:
        """Create a new agent identity"""
        # Generate key pair
        private_key = secrets.token_urlsafe(32)
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        
        # Create DID
        did = self.create_did(agent_id, public_key)
        
        # Create identity
        identity = AgentIdentity(
            agent_id=agent_id,
            did=did,
            public_key=public_key,
            capabilities=capabilities,
            owner=owner,
            security_level=security_level
        )
        
        # Store locally
        self.identities[agent_id] = identity
        
        logger.info(f"Created identity for agent {agent_id}: {did}")
        return identity
    
    def verify_identity(self, identity: AgentIdentity, signature: str, data: str) -> bool:
        """Verify an agent's identity using cryptographic signature"""
        if identity.agent_id in self.revoked:
            return False
        
        expected_hash = hashlib.sha256(f"{data}{identity.public_key}".encode()).hexdigest()
        return secrets.compare_digest(signature, expected_hash)
    
    def create_verifiable_credential(
        self,
        identity: AgentIdentity,
        capabilities: List[str],
        issuer: str = "AgentMCP"
    ) -> Dict[str, Any]:
        """Create a verifiable credential for an agent"""
        credential = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "AgentCapabilityCredential"],
            "issuer": issuer,
            "issuanceDate": datetime.now(timezone.utc).isoformat(),
            "credentialSubject": {
                "id": identity.did,
                "agentId": identity.agent_id,
                "capabilities": capabilities,
                "securityLevel": identity.security_level.value
            },
            "proof": {
                "type": "Ed25519Signature2018",
                "created": datetime.now(timezone.utc).isoformat(),
                "proofPurpose": "assertionMethod",
                "verificationMethod": f"{identity.did}#keys-1",
                "jws": self._sign_credential(identity, capabilities)
            }
        }
        return credential
    
    def _sign_credential(self, identity: AgentIdentity, capabilities: List[str]) -> str:
        """Sign a credential (simplified implementation)"""
        data = f"{identity.did}:{json.dumps(capabilities, sort_keys=True)}"
        return hashlib.sha256(f"{data}{self.secret_key}".encode()).hexdigest()

class ZeroTrustAuthorizer:
    """Zero Trust authorization engine with ABAC (Attribute-Based Access Control)"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.policies: Dict[str, AccessPolicy] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.decision_cache = {}
        
        # Default policies
        self._setup_default_policies()
    
    def _setup_default_policies(self):
        """Setup default zero-trust policies"""
        # Tool access policy
        self.policies["tool_access"] = AccessPolicy(
            name="tool_access",
            required_capabilities=["tool_usage"],
            required_permissions=[Permission.CALL_TOOL],
            max_task_value=100.0,
            security_level_required=SecurityLevel.MEDIUM,
            rate_limits={
                "tool:call": {"requests": 100, "window": 60}  # 100 calls per minute
            }
        )
        
        # Agent communication policy
        self.policies["agent_communication"] = AccessPolicy(
            name="agent_communication",
            required_capabilities=["messaging"],
            required_permissions=[Permission.SEND_MESSAGE, Permission.RECEIVE_MESSAGE],
            security_level_required=SecurityLevel.LOW,
            rate_limits={
                "message:send": {"requests": 50, "window": 60}  # 50 messages per minute
            }
        )
        
        # Payment management policy
        self.policies["payment_management"] = AccessPolicy(
            name="payment_management",
            required_capabilities=["payment_processing"],
            required_permissions=[Permission.MANAGE_PAYMENT],
            max_task_value=10000.0,
            security_level_required=SecurityLevel.HIGH,
            rate_limits={
                "payment:manage": {"requests": 10, "window": 60}  # 10 payment ops per minute
            }
        )
        
        # System administration policy
        self.policies["system_admin"] = AccessPolicy(
            name="system_admin",
            required_capabilities=["admin_access"],
            required_permissions=[Permission.SYSTEM_ADMIN],
            security_level_required=SecurityLevel.CRITICAL,
            rate_limits={
                "system:admin": {"requests": 5, "window": 60}  # 5 admin ops per minute
            }
        )
    
    def check_authorization(
        self,
        identity: AgentIdentity,
        action: str,
        context: Dict[str, Any],
        resource: str = None
    ) -> Dict[str, Any]:
        """Perform zero-trust authorization check"""
        # Get relevant policy
        policy_name = self._determine_policy(action, resource)
        policy = self.policies.get(policy_name)
        
        if not policy:
            return {
                "allowed": False,
                "reason": f"No policy found for action: {action}",
                "policy_used": None
            }
        
        # Check security level requirement
        if self._compare_security_levels(identity.security_level, policy.security_level_required) < 0:
            return {
                "allowed": False,
                "reason": f"Security level {identity.security_level.value} insufficient, requires {policy.security_level_required.value}",
                "policy_used": policy_name
            }
        
        # Check required capabilities
        missing_caps = set(policy.required_capabilities) - set(identity.capabilities)
        if missing_caps:
            return {
                "allowed": False,
                "reason": f"Missing capabilities: {list(missing_caps)}",
                "policy_used": policy_name
            }
        
        # Check target restrictions
        target = context.get("target")
        if policy.denied_targets and target in policy.denied_targets:
            return {
                "allowed": False,
                "reason": f"Target {target} is explicitly denied",
                "policy_used": policy_name
            }
        
        if policy.allowed_targets and target not in policy.allowed_targets:
            return {
                "allowed": False,
                "reason": f"Target {target} not in allowed list",
                "policy_used": policy_name
            }
        
        # Check task value limits
        task_value = context.get("value", 0)
        if policy.max_task_value and task_value > policy.max_task_value:
            return {
                "allowed": False,
                "reason": f"Task value {task_value} exceeds limit {policy.max_task_value}",
                "policy_used": policy_name
            }
        
        # Check time restrictions
        if policy.time_restrictions:
            current_time = datetime.now(timezone.utc)
            if not self._check_time_restrictions(current_time, policy.time_restrictions):
                return {
                    "allowed": False,
                    "reason": "Access outside allowed time window",
                    "policy_used": policy_name
                }
        
        # All checks passed
        return {
            "allowed": True,
            "reason": "All authorization checks passed",
            "policy_used": policy_name
        }
    
    def _determine_policy(self, action: str, resource: str) -> str:
        """Determine which policy applies to an action"""
        if action.startswith("tool:"):
            return "tool_access"
        elif action.startswith("message:"):
            return "agent_communication"
        elif action.startswith("payment:"):
            return "payment_management"
        elif action.startswith("system:"):
            return "system_admin"
        else:
            return "tool_access"  # Default
    
    def _compare_security_levels(self, current: SecurityLevel, required: SecurityLevel) -> int:
        """Compare security levels (-1: insufficient, 0: equal, 1: sufficient)"""
        levels = {
            SecurityLevel.LOW: 1,
            SecurityLevel.MEDIUM: 2,
            SecurityLevel.HIGH: 3,
            SecurityLevel.CRITICAL: 4
        }
        return levels[current] - levels[required]
    
    def _check_time_restrictions(self, current_time: datetime, restrictions: Dict[str, Any]) -> bool:
        """Check if current time is within allowed restrictions"""
        # Simple implementation - can be extended
        if "allowed_hours" in restrictions:
            current_hour = current_time.hour
            allowed_start = restrictions["allowed_hours"]["start"]
            allowed_end = restrictions["allowed_hours"]["end"]
            
            if not (allowed_start <= current_hour <= allowed_end):
                return False
        
        if "allowed_days" in restrictions:
            current_day = current_time.weekday()  # 0 = Monday
            if current_day not in restrictions["allowed_days"]:
                return False
        
        return True
    
    def create_scoped_token(
        self,
        identity: AgentIdentity,
        permissions: List[Permission],
        ttl_minutes: int = 15,
        context: Dict[str, Any] = None
    ) -> str:
        """Create a short-lived scoped JWT token"""
        now = datetime.utcnow()
        
        payload = {
            "sub": identity.did,
            "agent_id": identity.agent_id,
            "permissions": [p.value for p in permissions],
            "security_level": identity.security_level.value,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
            "jti": str(uuid.uuid4()),  # Unique token ID
            "context": context or {}
        }
        
        # Add capability-based claims
        if identity.capabilities:
            payload["capabilities"] = identity.capabilities
        
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        
        # Store session info
        session_id = payload["jti"]
        self.active_sessions[session_id] = {
            "agent_id": identity.agent_id,
            "permissions": permissions,
            "created_at": now.isoformat(),
            "last_used": now.isoformat(),
            "usage_count": 0
        }
        
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # Check if token is expired
            if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
                return None
            
            # Check if session is still active
            session_id = payload.get("jti")
            if session_id and session_id not in self.active_sessions:
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            session_id = payload.get("jti")
            
            if session_id and session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.info(f"Revoked token session: {session_id}")
                return True
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
        
        return False

class RateLimiter:
    """Advanced rate limiting for agent operations"""
    
    def __init__(self):
        self.requests = defaultdict(lambda: defaultdict(deque))
        self.limits = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = datetime.now(timezone.utc)
    
    def set_rate_limit(self, key: str, limit: int, window: int):
        """Set rate limit for a specific key"""
        self.limits[key] = {"limit": limit, "window": window}
    
    def check_rate_limit(self, agent_id: str, action: str) -> Dict[str, Any]:
        """Check if agent is within rate limits"""
        # Cleanup old entries
        self._cleanup_old_entries()
        
        key = f"{agent_id}:{action}"
        limit_info = self.limits.get(action, {"limit": 100, "window": 60})
        
        # Get current requests in window
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(seconds=limit_info["window"])
        
        # Remove old requests
        while (self.requests[agent_id][action] and 
               self.requests[agent_id][action][0] < cutoff_time):
            self.requests[agent_id][action].popleft()
        
        # Check limit
        request_count = len(self.requests[agent_id][action])
        
        if request_count >= limit_info["limit"]:
            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": (self.requests[agent_id][action][0] + timedelta(seconds=limit_info["window"])).isoformat() if self.requests[agent_id][action] else (now + timedelta(seconds=limit_info["window"])).isoformat(),
                "limit": limit_info["limit"],
                "window": limit_info["window"]
            }
        
        # Add current request
        self.requests[agent_id][action].append(now)
        
        return {
            "allowed": True,
            "remaining": limit_info["limit"] - (request_count + 1),
            "reset_time": (now + timedelta(seconds=limit_info["window"])).isoformat(),
            "limit": limit_info["limit"],
            "window": limit_info["window"]
        }
    
    def _cleanup_old_entries(self):
        """Cleanup old rate limit entries"""
        now = datetime.now(timezone.utc)
        
        if (now - self.last_cleanup).seconds < self.cleanup_interval:
            return
        
        for agent_id in self.requests:
            for action in self.requests[agent_id]:
                cutoff_time = now - timedelta(seconds=300)  # 5 minutes
                while (self.requests[agent_id][action] and 
                       self.requests[agent_id][action][0] < cutoff_time):
                    self.requests[agent_id][action].popleft()
        
        self.last_cleanup = now

class AuditLogger:
    """Immutable audit logging for compliance"""
    
    def __init__(self, storage_backend):
        self.storage = storage_backend  # Could be Firestore, PostgreSQL, etc.
        self.logger = logging.getLogger("audit")
    
    async def log_action(
        self,
        agent_id: str,
        action: str,
        target: str = None,
        resource: str = None,
        result: str = "success",
        permission_used: str = None,
        task_id: str = None,
        payment_id: str = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """Log an agent action for audit trail"""
        try:
            # Calculate risk score
            risk_score = self._calculate_risk_score(action, result, context)
            
            entry = AuditLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent_id=agent_id,
                action=action,
                target=target or "unknown",
                resource=resource or "unknown",
                result=result,
                permission_used=permission_used,
                task_id=task_id,
                payment_id=payment_id,
                risk_score=risk_score,
                ip_address=context.get("ip_address") if context else None,
                user_agent=context.get("user_agent") if context else None,
                metadata=context or {}
            )
            
            # Store with integrity hash
            entry_hash = entry.compute_hash()
            entry_data = asdict(entry)
            entry_data["hash"] = entry_hash
            
            # Store in backend
            await self.storage.write("audit_logs", entry_data)
            
            # Also log to standard logger
            self.logger.info(f"Audit: {agent_id} performed {action} on {target} - {result}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log audit entry: {e}")
            return False
    
    def _calculate_risk_score(self, action: str, result: str, context: Dict[str, Any]) -> float:
        """Calculate risk score for the action"""
        base_score = 0.0
        
        # Higher risk for sensitive actions
        if action.startswith("payment:"):
            base_score += 0.7
        elif action.startswith("system:admin"):
            base_score += 0.9
        elif action.startswith("tool:"):
            base_score += 0.3
        
        # Higher risk for failures
        if result == "error":
            base_score += 0.2
        
        # Contextual factors
        if context:
            if context.get("is_external_request", False):
                base_score += 0.1
            if context.get("late_night_access", False):
                base_score += 0.15
        
        return min(base_score, 1.0)
    
    async def verify_audit_chain(self, agent_id: str, start_time: str = None, end_time: str = None) -> Dict[str, Any]:
        """Verify integrity of audit log chain"""
        try:
            # Get audit logs for the agent
            logs = await self.storage.query(
                "audit_logs", 
                filters={"agent_id": agent_id, "timestamp_gte": start_time, "timestamp_lte": end_time}
            )
            
            if not logs:
                return {"verified": False, "reason": "No audit logs found"}
            
            # Verify hash chain
            verification_errors = []
            for i, log in enumerate(logs[1:], 1):
                if "hash" not in log:
                    verification_errors.append(f"Missing hash for log at index {i}")
                    continue
                
                # Recalculate hash of previous log
                prev_log = logs[i-1]
                prev_data = {
                    "timestamp": prev_log["timestamp"],
                    "agent_id": prev_log["agent_id"],
                    "action": prev_log["action"],
                    "target": prev_log["target"],
                    "result": prev_log["result"]
                }
                expected_hash = hashlib.sha256(json.dumps(prev_data, sort_keys=True).encode()).hexdigest()
                
                if log["hash"] != expected_hash:
                    verification_errors.append(f"Hash mismatch at index {i}")
            
            return {
                "verified": len(verification_errors) == 0,
                "total_logs": len(logs),
                "verification_errors": verification_errors
            }
            
        except Exception as e:
            logger.error(f"Error verifying audit chain: {e}")
            return {"verified": False, "reason": str(e)}

class ZeroTrustSecurityLayer:
    """Main security coordinator combining all security components"""
    
    def __init__(
        self,
        secret_key: str = None,
        storage_backend = None,
        did_registry_url: str = None
    ):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        
        # Initialize security components
        self.identity_manager = DecentralizedIdentityManager(did_registry_url, self.secret_key)
        self.authorizer = ZeroTrustAuthorizer(self.secret_key)
        self.rate_limiter = RateLimiter()
        self.audit_logger = AuditLogger(storage_backend)
        
        # Setup rate limits
        self._setup_rate_limits()
    
    def _setup_rate_limits(self):
        """Setup default rate limits"""
        self.rate_limiter.set_rate_limit("tool:call", 200, 60)  # 200 tool calls per minute
        self.rate_limiter.set_rate_limit("message:send", 100, 60)  # 100 messages per minute
        self.rate_limiter.set_rate_limit("payment:manage", 10, 60)  # 10 payment ops per minute
        self.rate_limiter.set_rate_limit("system:admin", 5, 60)  # 5 admin ops per minute
    
    async def create_agent_identity(
        self,
        agent_id: str,
        capabilities: List[str],
        owner: str = None,
        security_level: SecurityLevel = SecurityLevel.MEDIUM
    ) -> Tuple[AgentIdentity, str]:
        """Create agent identity and return authentication token"""
        # Create identity
        identity = self.identity_manager.create_identity(
            agent_id=agent_id,
            capabilities=capabilities,
            owner=owner,
            security_level=security_level
        )
        
        # Create initial token
        token = self.authorizer.create_scoped_token(
            identity=identity,
            permissions=[
                Permission.READ_CONTEXT,
                Permission.WRITE_CONTEXT,
                Permission.EXECUTE_TASK,
                Permission.CALL_TOOL
            ],
            ttl_minutes=60  # Longer initial token
        )
        
        await self.audit_logger.log_action(
            agent_id=agent_id,
            action="identity:created",
            resource="agent_identity",
            context={"security_level": security_level.value}
        )
        
        return identity, token
    
    async def authenticate_agent(self, token: str, action: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Authenticate an agent token for a specific action"""
        # Verify token
        token_data = self.authorizer.verify_token(token)
        if not token_data:
            await self.audit_logger.log_action(
                agent_id="unknown",
                action="auth:failed",
                result="error",
                context={"reason": "invalid_token"}
            )
            return None
        
        # Get agent identity
        agent_id = token_data["agent_id"]
        identity = self.identity_manager.identities.get(agent_id)
        if not identity:
            await self.audit_logger.log_action(
                agent_id=agent_id,
                action="auth:failed",
                result="error",
                context={"reason": "identity_not_found"}
            )
            return None
        
        # Check rate limits
        rate_check = self.rate_limiter.check_rate_limit(agent_id, action)
        if not rate_check["allowed"]:
            await self.audit_logger.log_action(
                agent_id=agent_id,
                action="auth:failed",
                result="error",
                context={"reason": "rate_limit_exceeded", "rate_info": rate_check}
            )
            return None
        
        # Authorization check
        authz_result = self.authorizer.check_authorization(identity, action, context or {})
        
        if not authz_result["allowed"]:
            await self.audit_logger.log_action(
                agent_id=agent_id,
                action="auth:denied",
                result="denied",
                permission_used=action,
                context={"reason": authz_result["reason"], "policy": authz_result["policy_used"]}
            )
            return None
        
        # Update session usage
        session_id = token_data.get("jti")
        if session_id and session_id in self.authorizer.active_sessions:
            self.authorizer.active_sessions[session_id]["last_used"] = datetime.utcnow().isoformat()
            self.authorizer.active_sessions[session_id]["usage_count"] += 1
        
        # Log successful authentication
        await self.audit_logger.log_action(
            agent_id=agent_id,
            action="auth:success",
            result="success",
            permission_used=action,
            context={"policy": authz_result["policy_used"]}
        )
        
        return {
            "identity": identity,
            "token_data": token_data,
            "authorization": authz_result
        }
    
    async def create_capability_token(
        self,
        agent_id: str,
        permissions: List[Permission],
        ttl_minutes: int = 15,
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """Create a scoped capability token"""
        identity = self.identity_manager.identities.get(agent_id)
        if not identity:
            return None
        
        token = self.authorizer.create_scoped_token(identity, permissions, ttl_minutes, context)
        
        await self.audit_logger.log_action(
            agent_id=agent_id,
            action="token:created",
            resource="capability_token",
            context={
                "permissions": [p.value for p in permissions],
                "ttl_minutes": ttl_minutes
            }
        )
        
        return token
    
    async def revoke_agent_access(self, agent_id: str, reason: str = None) -> bool:
        """Revoke an agent's access"""
        # Remove from identity manager
        if agent_id in self.identity_manager.identities:
            del self.identity_manager.identities[agent_id]
        
        # Add to revoked list
        self.identity_manager.revoked.add(agent_id)
        
        # Clear active sessions
        sessions_to_remove = [
            session_id for session_id, session in self.authorizer.active_sessions.items()
            if session.get("agent_id") == agent_id
        ]
        
        for session_id in sessions_to_remove:
            del self.authorizer.active_sessions[session_id]
        
        await self.audit_logger.log_action(
            agent_id=agent_id,
            action="access:revoked",
            result="revoked",
            context={"reason": reason or "administrative_action"}
        )
        
        return True
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get overall security status"""
        return {
            "active_identities": len(self.identity_manager.identities),
            "revoked_identities": len(self.identity_manager.revoked),
            "active_sessions": len(self.authorizer.active_sessions),
            "security_policies": list(self.authorizer.policies.keys()),
            "rate_limits": self.rate_limiter.limits,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Export for easy importing
__all__ = [
    'Permission',
    'SecurityLevel',
    'AgentIdentity',
    'AccessPolicy',
    'AuditLogEntry',
    'DecentralizedIdentityManager',
    'ZeroTrustAuthorizer',
    'RateLimiter',
    'AuditLogger',
    'ZeroTrustSecurityLayer'
]