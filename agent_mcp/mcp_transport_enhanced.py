"""
Enhanced MCP Transport Layer with transaction support.
"""

from .mcp_transport import MCPTransport, HTTPTransport
from .mcp_transaction import MCPTransaction, MCPPayment
from typing import Dict, Any, Optional

class TransactionalHTTPTransport(HTTPTransport):
    """HTTP transport with transaction support"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_manager = MCPTransaction()
        self.payment_manager = MCPPayment()
        
    async def send_message(self, target: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message with transaction support"""
        # Start transaction
        transaction_id = await self.transaction_manager.begin_transaction(
            sender=self.agent_name,
            receiver=target,
            metadata={"message_type": message.get("type")}
        )
        
        try:
            # Process any payments if needed
            if "payment" in message:
                payment_id = await self.payment_manager.process_payment(
                    sender=self.agent_name,
                    receiver=target,
                    amount=message["payment"]["amount"]
                )
                message["payment"]["id"] = payment_id
            
            # Send the message
            result = await super().send_message(target, message)
            
            # Commit transaction
            await self.transaction_manager.commit_transaction(transaction_id)
            return result
            
        except Exception as e:
            # Rollback on failure
            await self.transaction_manager.rollback_transaction(transaction_id)
            raise e
