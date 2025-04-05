"""
MCP Network Server - Central hub for agent communication.
"""

from fastapi import FastAPI, Request, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
import uvicorn
import asyncio
from typing import Dict, Set, Any, Optional
import json
from datetime import datetime
import os
from firebase_admin import credentials, firestore, initialize_app
import google.cloud.firestore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Initialize Firebase
cred = credentials.Certificate(os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'firebase-key.json'))
firebase_app = initialize_app(cred)
db = firestore.client()

app = FastAPI(title="MCP Network Server")
security = HTTPBearer()

class MessageQueue:
    def __init__(self):
        self.messages_ref = db.collection('messages')
    
    async def push_message(self, target_id: str, message: dict):
        """Push a message to the target's queue"""
        message["timestamp"] = datetime.utcnow()
        await self.messages_ref.document(target_id).collection('queue').add(message)
        
        # Keep only last 100 messages
        old_messages = self.messages_ref.document(target_id).collection('queue').order_by(
            'timestamp', direction=firestore.Query.ASCENDING
        ).limit(100).stream()
        
        for old_msg in old_messages:
            old_msg.reference.delete()
    
    async def get_messages(self, agent_id: str) -> list:
        """Get all messages for an agent"""
        messages = self.messages_ref.document(agent_id).collection('queue')\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .limit(10).stream()
        return [msg.to_dict() for msg in messages]

class AgentRegistry:
    def __init__(self):
        self.agents_ref = db.collection('agents')
    
    async def register(self, agent_id: str, info: dict) -> str:
        """Register an agent"""
        info["last_seen"] = datetime.utcnow()
        await self.agents_ref.document(agent_id).set(info)
        return agent_id
    
    async def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get agent info"""
        doc = self.agents_ref.document(agent_id).get()
        return doc.to_dict() if doc.exists else None
    
    async def list_agents(self) -> dict:
        """List all agents"""
        agents = {}
        for doc in self.agents_ref.stream():
            agents[doc.id] = doc.to_dict()
        return agents
    
    async def heartbeat(self, agent_id: str):
        """Update agent's last seen timestamp"""
        await self.agents_ref.document(agent_id).update({
            'last_seen': datetime.utcnow()
        })

# Initialize services
message_queue = MessageQueue()
agent_registry = AgentRegistry()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        # Get agent info from Firestore
        agent = await agent_registry.get_agent(credentials.credentials)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"agent_id": credentials.credentials}
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/register")
async def register_agent(request: Request):
    """Register a new agent with the network"""
    data = await request.json()
    agent_id = data.get("agent_id")
    agent_info = data.get("info", {})
    
    # Register agent
    await agent_registry.register(agent_id, agent_info)
    
    # Generate JWT token
    token = jwt.encode(
        {"agent_id": agent_id, "type": agent_info.get("type")},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    
    return {
        "status": "registered",
        "agent_id": agent_id,
        "token": token
    }

@app.post("/message/{target_id}")
async def handle_message(
    target_id: str,
    request: Request,
    token_data: dict = Depends(verify_token)
):
    """Handle message delivery to target agent"""
    # Verify target exists
    target = await agent_registry.get_agent(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    message = await request.json()
    message["from"] = token_data["agent_id"]
    
    # Store message
    await message_queue.push_message(target_id, message)
    
    return {"status": "delivered"}

@app.get("/events/{agent_id}")
async def event_stream(
    agent_id: str,
    token_data: dict = Depends(verify_token)
):
    """SSE endpoint for real-time message delivery"""
    if token_data["agent_id"] != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    async def event_generator():
        try:
            while True:
                # Update heartbeat
                await agent_registry.heartbeat(agent_id)
                
                # Get new messages
                messages = await message_queue.get_messages(agent_id)
                if messages:
                    yield {
                        "event": "message",
                        "data": json.dumps(messages[0])  # Send newest message
                    }
                    # Remove sent message
                    await redis_conn.lpop(f"messages:{agent_id}")
                else:
                    yield {
                        "event": "heartbeat",
                        "data": "ping"
                    }
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            # Clean up on disconnect
            pass
    
    return EventSourceResponse(event_generator())

@app.get("/agents")
async def list_agents(token_data: dict = Depends(verify_token)):
    """List all connected agents"""
    agents = await agent_registry.list_agents()
    return {"agents": agents}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
