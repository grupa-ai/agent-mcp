"""
Hybrid Payment Gateway for AgentMCP
Business-friendly payment system supporting both traditional fiat and cryptocurrency

This module provides a comprehensive payment solution supporting:
- Traditional fiat payments via Stripe Connect
- Cryptocurrency payments via USDC on Base
- x402 Protocol for agent micropayments
- Agent Payments Protocol (AP2) integration
- Escrow services for task completion assurance
"""

import asyncio
import json
import uuid
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import aiohttp
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

# Try to import payment libraries
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None
    logger.warning("Stripe not available. Install with: pip install stripe")

try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    from eth_account import Account
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    Web3 = None
    Account = None
    logger.warning("Web3 not available. Install with: pip install web3")

class PaymentMethod(Enum):
    """Supported payment methods"""
    STRIPE = "stripe"
    USDC = "usdc"
    X402 = "x402"
    AP2 = "ap2"
    ESCROW = "escrow"

class PaymentStatus(Enum):
    """Payment status tracking"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    ESCROWED = "escrowed"

@dataclass
class PaymentRequest:
    """Standardized payment request structure"""
    sender_agent_id: str
    receiver_agent_id: str
    amount: float
    currency: str = "USD"
    task_id: str = None
    description: str = ""
    payment_method: PaymentMethod = PaymentMethod.STRIPE
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.task_id is None:
            self.task_id = str(uuid.uuid4())

@dataclass
class PaymentResponse:
    """Standardized payment response structure"""
    payment_id: str
    status: PaymentStatus
    amount: float
    currency: str
    sender_agent_id: str
    receiver_agent_id: str
    transaction_id: str = None
    block_number: int = None
    created_at: str = None
    completed_at: str = None
    fee: float = 0.0
    error_message: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()

class StripePaymentGateway:
    """Stripe Connect integration for fiat payments"""
    
    def __init__(self, api_key: str, webhook_secret: str = None):
        if not STRIPE_AVAILABLE:
            raise ImportError("Stripe is not installed")
        
        stripe.api_key = api_key
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.agent_accounts = {}
    
    async def create_agent_account(
        self,
        agent_id: str,
        email: str,
        business_name: str = None
    ) -> Dict[str, Any]:
        """Create a Stripe Connect account for an agent"""
        try:
            # Check if account already exists
            if agent_id in self.agent_accounts:
                return {
                    "status": "success",
                    "account_id": self.agent_accounts[agent_id]["account_id"],
                    "message": "Existing account retrieved"
                }
            
            # Create Express account
            account_data = {
                "type": "express",
                "country": "US",
                "email": email,
                "capabilities": ["card_payments", "transfers"],
                "business_type": "individual",
                "metadata": {
                    "agent_id": agent_id,
                    "created_by": "AgentMCP"
                }
            }
            
            if business_name:
                account_data["business_profile"] = {
                    "name": business_name,
                    "product_description": "AI Agent Services"
                }
            
            account = stripe.Account.create(**account_data)
            
            # Store account info
            self.agent_accounts[agent_id] = {
                "account_id": account.id,
                "email": email,
                "business_name": business_name,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return {
                "status": "success",
                "account_id": account.id,
                "account_link": account.get("account_links", [{}])[0].get("url"),
                "message": "Stripe Connect account created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating Stripe account for agent {agent_id}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process a fiat payment via Stripe"""
        try:
            # Get receiver's Stripe account
            receiver_account = await self._get_agent_account(request.receiver_agent_id)
            if not receiver_account:
                return PaymentResponse(
                    payment_id=str(uuid.uuid4()),
                    status=PaymentStatus.FAILED,
                    amount=request.amount,
                    currency=request.currency,
                    sender_agent_id=request.sender_agent_id,
                    receiver_agent_id=request.receiver_agent_id,
                    error_message="Receiver account not found"
                )
            
            # Create payment intent with transfer
            amount_cents = int(request.amount * 100)  # Convert to cents
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=request.currency.lower(),
                transfer_data={
                    "destination": receiver_account["account_id"],
                    "amount": amount_cents - int(self._calculate_fee(request.amount) * 100)  # Subtract fee
                },
                metadata={
                    "sender_agent_id": request.sender_agent_id,
                    "receiver_agent_id": request.receiver_agent_id,
                    "task_id": request.task_id,
                    "agentmcp_payment": "true"
                },
                description=request.description or f"Payment from {request.sender_agent_id} to {request.receiver_agent_id}"
            )
            
            return PaymentResponse(
                payment_id=payment_intent.id,
                status=self._convert_stripe_status(payment_intent.status),
                amount=request.amount,
                currency=request.currency,
                sender_agent_id=request.sender_agent_id,
                receiver_agent_id=request.receiver_agent_id,
                transaction_id=payment_intent.charges.data[0].id if payment_intent.charges.data else None,
                fee=self._calculate_fee(request.amount),
                created_at=datetime.fromtimestamp(payment_intent.created, timezone.utc).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error processing Stripe payment: {e}")
            return PaymentResponse(
                payment_id=str(uuid.uuid4()),
                status=PaymentStatus.FAILED,
                amount=request.amount,
                currency=request.currency,
                sender_agent_id=request.sender_agent_id,
                receiver_agent_id=request.receiver_agent_id,
                error_message=str(e)
            )
    
    async def create_escrow_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Create an escrow payment held until task completion"""
        try:
            amount_cents = int(request.amount * 100)
            
            # Create payment intent with manual capture (authorization only)
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=request.currency.lower(),
                capture_method="manual",  # Don't capture immediately
                metadata={
                    "sender_agent_id": request.sender_agent_id,
                    "receiver_agent_id": request.receiver_agent_id,
                    "task_id": request.task_id,
                    "escrow": "true",
                    "agentmcp_payment": "true"
                },
                description=f"Escrow payment for task {request.task_id}"
            )
            
            return PaymentResponse(
                payment_id=payment_intent.id,
                status=PaymentStatus.ESCROWED,
                amount=request.amount,
                currency=request.currency,
                sender_agent_id=request.sender_agent_id,
                receiver_agent_id=request.receiver_agent_id,
                transaction_id=payment_intent.charges.data[0].id if payment_intent.charges.data else None,
                created_at=datetime.fromtimestamp(payment_intent.created, timezone.utc).isoformat(),
                metadata={"escrow_release_required": True}
            )
            
        except Exception as e:
            logger.error(f"Error creating Stripe escrow: {e}")
            return PaymentResponse(
                payment_id=str(uuid.uuid4()),
                status=PaymentStatus.FAILED,
                amount=request.amount,
                currency=request.currency,
                sender_agent_id=request.sender_agent_id,
                receiver_agent_id=request.receiver_agent_id,
                error_message=str(e)
            )
    
    async def release_escrow(self, payment_id: str) -> PaymentResponse:
        """Release captured escrow payment"""
        try:
            # Retrieve the payment intent
            payment_intent = stripe.PaymentIntent.retrieve(payment_id)
            
            if payment_intent.status != "requires_capture":
                return PaymentResponse(
                    payment_id=payment_id,
                    status=PaymentStatus.FAILED,
                    amount=payment_intent.amount / 100,
                    currency=payment_intent.currency.upper(),
                    sender_agent_id=payment_intent.metadata.get("sender_agent_id"),
                    receiver_agent_id=payment_intent.metadata.get("receiver_agent_id"),
                    error_message="Payment is not in escrow"
                )
            
            # Capture the payment
            captured_payment = stripe.PaymentIntent.capture(payment_id)
            
            return PaymentResponse(
                payment_id=payment_id,
                status=self._convert_stripe_status(captured_payment.status),
                amount=captured_payment.amount / 100,
                currency=captured_payment.currency.upper(),
                sender_agent_id=payment_intent.metadata.get("sender_agent_id"),
                receiver_agent_id=payment_intent.metadata.get("receiver_agent_id"),
                transaction_id=captured_payment.charges.data[0].id if captured_payment.charges.data else None,
                completed_at=datetime.fromtimestamp(captured_payment.created, timezone.utc).isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error releasing escrow {payment_id}: {e}")
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=0,
                currency="USD",
                sender_agent_id="unknown",
                receiver_agent_id="unknown",
                error_message=str(e)
            )
    
    async def _get_agent_account(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get Stripe account info for an agent"""
        return self.agent_accounts.get(agent_id)
    
    def _calculate_fee(self, amount: float) -> float:
        """Calculate payment fee (2.9% + $0.30)"""
        return round((amount * 0.029) + 0.30, 2)
    
    def _convert_stripe_status(self, stripe_status: str) -> PaymentStatus:
        """Convert Stripe status to PaymentStatus"""
        status_mapping = {
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.PROCESSING,
            "processing": PaymentStatus.PROCESSING,
            "succeeded": PaymentStatus.COMPLETED,
            "canceled": PaymentStatus.FAILED
        }
        return status_mapping.get(stripe_status, PaymentStatus.FAILED)

class USDCPaymentGateway:
    """USDC payment gateway on Base blockchain"""
    
    def __init__(self, rpc_url: str, private_key: str, usdc_contract: str = None):
        if not WEB3_AVAILABLE:
            raise ImportError("Web3 is not installed")
        
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # USDC contract on Base
        self.usdc_address = usdc_contract or "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        
        # USDC ABI (minimal for transfers)
        self.usdc_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "payable": False,
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        
        self.contract = self.w3.eth.contract(
            address=self.usdc_address,
            abi=self.usdc_abi
        )
        
        self.agent_wallets = {}
    
    async def create_agent_wallet(self, agent_id: str) -> Dict[str, Any]:
        """Create or derive a wallet for an agent"""
        try:
            if agent_id in self.agent_wallets:
                return {
                    "status": "success",
                    "address": self.agent_wallets[agent_id]["address"],
                    "message": "Existing wallet retrieved"
                }
            
            # Derive deterministic wallet from agent_id
            # In production, use HD wallet derivation
            wallet_seed = hashlib.sha256(f"agent:{agent_id}:{self.private_key}".encode()).hexdigest()
            agent_wallet = Account.from_key(wallet_seed)
            
            self.agent_wallets[agent_id] = {
                "address": agent_wallet.address,
                "private_key": wallet_seed,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            return {
                "status": "success",
                "address": agent_wallet.address,
                "message": "Agent wallet created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating agent wallet: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process USDC payment on Base"""
        try:
            # Get receiver wallet
            receiver_wallet = await self._get_agent_wallet(request.receiver_agent_id)
            if not receiver_wallet:
                return PaymentResponse(
                    payment_id=str(uuid.uuid4()),
                    status=PaymentStatus.FAILED,
                    amount=request.amount,
                    currency="USDC",
                    sender_agent_id=request.sender_agent_id,
                    receiver_agent_id=request.receiver_agent_id,
                    error_message="Receiver wallet not found"
                )
            
            # Convert USDC amount (6 decimals)
            amount_usdc = int(request.amount * 1e6)
            
            # Get current gas price
            gas_price = self.w3.eth.gas_price
            gas_limit = 100000  # Estimate for ERC20 transfer
            gas_cost = self.w3.from_wei(gas_price * gas_limit, 'ether')
            
            # Build transaction
            transaction = {
                'from': self.address,
                'to': self.usdc_address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.address),
                'data': self.contract.encodeABI(
                    fn_name='transfer',
                    args=[receiver_wallet["address"], amount_usdc]
                )
            }
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                return PaymentResponse(
                    payment_id=tx_hash.hex(),
                    status=PaymentStatus.COMPLETED,
                    amount=request.amount,
                    currency="USDC",
                    sender_agent_id=request.sender_agent_id,
                    receiver_agent_id=request.receiver_agent_id,
                    transaction_id=tx_hash.hex(),
                    block_number=receipt.blockNumber,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    fee=float(gas_cost)
                )
            else:
                return PaymentResponse(
                    payment_id=tx_hash.hex(),
                    status=PaymentStatus.FAILED,
                    amount=request.amount,
                    currency="USDC",
                    sender_agent_id=request.sender_agent_id,
                    receiver_agent_id=request.receiver_agent_id,
                    transaction_id=tx_hash.hex(),
                    error_message="Transaction failed on blockchain"
                )
                
        except Exception as e:
            logger.error(f"Error processing USDC payment: {e}")
            return PaymentResponse(
                payment_id=str(uuid.uuid4()),
                status=PaymentStatus.FAILED,
                amount=request.amount,
                currency="USDC",
                sender_agent_id=request.sender_agent_id,
                receiver_agent_id=request.receiver_agent_id,
                error_message=str(e)
            )
    
    async def _get_agent_wallet(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet info for an agent"""
        return self.agent_wallets.get(agent_id)

class X402PaymentGateway:
    """x402 Protocol implementation for HTTP 402 payments"""
    
    def __init__(self, gateway_url: str, api_key: str = None):
        self.gateway_url = gateway_url
        self.api_key = api_key
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process payment via x402 protocol"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Create x402 payment header
            payment_header = self._create_payment_header(request.amount)
            
            # Build x402 request
            x402_request = {
                "receiver": request.receiver_agent_id,
                "amount": str(request.amount),
                "currency": request.currency,
                "task_id": request.task_id,
                "description": request.description,
                "sender": request.sender_agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            headers = {
                "X-402-Payment": payment_header,
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            async with self.session.post(
                f"{self.gateway_url}/pay",
                json=x402_request,
                headers=headers
            ) as response:
                if response.status == 402:  # Expected x402 response
                    result = await response.json()
                    return PaymentResponse(
                        payment_id=result.get("payment_id", str(uuid.uuid4())),
                        status=self._convert_x402_status(result.get("status", "pending")),
                        amount=request.amount,
                        currency=request.currency,
                        sender_agent_id=request.sender_agent_id,
                        receiver_agent_id=request.receiver_agent_id,
                        transaction_id=result.get("transaction_id"),
                        metadata={"x402_gateway": True}
                    )
                else:
                    return PaymentResponse(
                        payment_id=str(uuid.uuid4()),
                        status=PaymentStatus.FAILED,
                        amount=request.amount,
                        currency=request.currency,
                        sender_agent_id=request.sender_agent_id,
                        receiver_agent_id=request.receiver_agent_id,
                        error_message=f"x402 gateway error: HTTP {response.status}"
                    )
                    
        except Exception as e:
            logger.error(f"Error processing x402 payment: {e}")
            return PaymentResponse(
                payment_id=str(uuid.uuid4()),
                status=PaymentStatus.FAILED,
                amount=request.amount,
                currency=request.currency,
                sender_agent_id=request.sender_agent_id,
                receiver_agent_id=request.receiver_agent_id,
                error_message=str(e)
            )
    
    def _create_payment_header(self, amount: float) -> str:
        """Create x402 payment header"""
        # Simplified x402 header - in production use proper cryptographic signing
        timestamp = str(int(time.time()))
        amount_str = str(amount)
        signature = hashlib.sha256(f"{amount_str}:{timestamp}:{self.api_key}".encode()).hexdigest()
        
        return f"x402 amount={amount_str}, ts={timestamp}, sig={signature}"
    
    def _convert_x402_status(self, x402_status: str) -> PaymentStatus:
        """Convert x402 status to PaymentStatus"""
        status_mapping = {
            "pending": PaymentStatus.PENDING,
            "processing": PaymentStatus.PROCESSING,
            "completed": PaymentStatus.COMPLETED,
            "failed": PaymentStatus.FAILED,
            "refunded": PaymentStatus.REFUNDED
        }
        return status_mapping.get(x402_status, PaymentStatus.FAILED)

class HybridPaymentGateway:
    """Unified payment gateway supporting multiple payment methods"""
    
    def __init__(
        self,
        stripe_config: Dict[str, str] = None,
        usdc_config: Dict[str, str] = None,
        x402_config: Dict[str, str] = None
    ):
        # Initialize payment gateways
        self.stripe_gateway = None
        if stripe_config and stripe_config.get("api_key"):
            self.stripe_gateway = StripePaymentGateway(
                stripe_config["api_key"],
                stripe_config.get("webhook_secret")
            )
        
        self.usdc_gateway = None
        if usdc_config and usdc_config.get("rpc_url") and usdc_config.get("private_key"):
            self.usdc_gateway = USDCPaymentGateway(
                usdc_config["rpc_url"],
                usdc_config["private_key"],
                usdc_config.get("usdc_contract")
            )
        
        self.x402_gateway = None
        if x402_config and x402_config.get("gateway_url"):
            self.x402_gateway = X402PaymentGateway(
                x402_config["gateway_url"],
                x402_config.get("api_key")
            )
        
        self.payment_history = []
    
    async def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process payment using the specified method"""
        try:
            # Log payment attempt
            logger.info(f"Processing payment: {request.sender_agent_id} -> {request.receiver_agent_id}, {request.amount} {request.currency} via {request.payment_method.value}")
            
            # Route to appropriate gateway
            if request.payment_method == PaymentMethod.STRIPE and self.stripe_gateway:
                return await self.stripe_gateway.process_payment(request)
            elif request.payment_method == PaymentMethod.USDC and self.usdc_gateway:
                return await self.usdc_gateway.process_payment(request)
            elif request.payment_method == PaymentMethod.X402 and self.x402_gateway:
                async with self.x402_gateway as gateway:
                    return await gateway.process_payment(request)
            else:
                return PaymentResponse(
                    payment_id=str(uuid.uuid4()),
                    status=PaymentStatus.FAILED,
                    amount=request.amount,
                    currency=request.currency,
                    sender_agent_id=request.sender_agent_id,
                    receiver_agent_id=request.receiver_agent_id,
                    error_message=f"Payment method {request.payment_method.value} not supported or not configured"
                )
        except Exception as e:
            logger.error(f"Error in hybrid payment gateway: {e}")
            return PaymentResponse(
                payment_id=str(uuid.uuid4()),
                status=PaymentStatus.FAILED,
                amount=request.amount,
                currency=request.currency,
                sender_agent_id=request.sender_agent_id,
                receiver_agent_id=request.receiver_agent_id,
                error_message=str(e)
            )
    
    async def create_escrow_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Create escrow payment (Stripe only for now)"""
        if self.stripe_gateway:
            return await self.stripe_gateway.create_escrow_payment(request)
        else:
            return PaymentResponse(
                payment_id=str(uuid.uuid4()),
                status=PaymentStatus.FAILED,
                amount=request.amount,
                currency=request.currency,
                sender_agent_id=request.sender_agent_id,
                receiver_agent_id=request.receiver_agent_id,
                error_message="Escrow not supported for this payment method"
            )
    
    async def release_escrow(self, payment_id: str) -> PaymentResponse:
        """Release escrow payment"""
        if self.stripe_gateway:
            return await self.stripe_gateway.release_escrow(payment_id)
        else:
            return PaymentResponse(
                payment_id=payment_id,
                status=PaymentStatus.FAILED,
                amount=0,
                currency="USD",
                sender_agent_id="unknown",
                receiver_agent_id="unknown",
                error_message="Escrow release not supported"
            )
    
    async def setup_agent_accounts(
        self,
        agent_id: str,
        email: str = None,
        business_name: str = None
    ) -> Dict[str, Any]:
        """Setup payment accounts for an agent across all gateways"""
        results = {}
        
        # Setup Stripe account
        if self.stripe_gateway:
            stripe_result = await self.stripe_gateway.create_agent_account(
                agent_id, email or f"{agent_id}@agentmcp.com", business_name
            )
            results["stripe"] = stripe_result
        
        # Setup USDC wallet
        if self.usdc_gateway:
            usdc_result = await self.usdc_gateway.create_agent_wallet(agent_id)
            results["usdc"] = usdc_result
        
        # Store results
        self.payment_history.append({
            "agent_id": agent_id,
            "action": "account_setup",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results
        })
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "accounts": results
        }
    
    def get_supported_methods(self) -> List[Dict[str, Any]]:
        """Get list of supported payment methods"""
        methods = []
        
        if self.stripe_gateway:
            methods.append({
                "method": PaymentMethod.STRIPE.value,
                "display_name": "Stripe (Fiat)",
                "currencies": ["USD", "EUR", "GBP"],
                "fees": "2.9% + $0.30",
                "escrow_supported": True,
                "min_amount": 0.50,
                "max_amount": 999999.99
            })
        
        if self.usdc_gateway:
            methods.append({
                "method": PaymentMethod.USDC.value,
                "display_name": "USDC (Base Blockchain)",
                "currencies": ["USDC"],
                "fees": "~$0.01 gas",
                "escrow_supported": False,
                "min_amount": 0.01,
                "max_amount": None
            })
        
        if self.x402_gateway:
            methods.append({
                "method": PaymentMethod.X402.value,
                "display_name": "x402 Protocol",
                "currencies": ["USD", "USDC", "EUR"],
                "fees": "Varies by provider",
                "escrow_supported": False,
                "min_amount": 0.01,
                "max_amount": None
            })
        
        return methods
    
    async def get_payment_history(
        self,
        agent_id: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get payment history"""
        history = self.payment_history
        
        if agent_id:
            history = [
                record for record in history
                if record.get("sender_agent_id") == agent_id or record.get("receiver_agent_id") == agent_id
            ]
        
        return sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]

# Export classes for easy importing
__all__ = [
    'PaymentMethod',
    'PaymentStatus',
    'PaymentRequest',
    'PaymentResponse',
    'StripePaymentGateway',
    'USDCPaymentGateway',
    'X402PaymentGateway',
    'HybridPaymentGateway'
]