"""
MCP Network Server - Central hub for agent communication.
"""

from fastapi import Request, Depends, HTTPException, APIRouter
from fastapi.responses import StreamingResponse
from firebase_admin import initialize_app, get_app, credentials, firestore
import uvicorn
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Set, Any, Optional
import json
import os
from firebase_admin import credentials, firestore
import google.cloud.firestore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from functools import lru_cache
from dotenv import load_dotenv
import sys

# Try to load .env file for local development
load_dotenv()

# Check if we're running in Firebase Cloud Functions
try:
    import firebase_functions
    IS_FIREBASE = True
except ImportError:
    IS_FIREBASE = False

# Initialize Firebase
db = None

def find_firebase_key():
    # 1. Check environment variable first (most reliable in cloud environments)
    key_path_env = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if key_path_env and os.path.exists(key_path_env):
        print(f"Using Firebase key from env var: {key_path_env}")
        return key_path_env

    # 2. Check for key file in the current directory (functions/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_key_path = os.path.join(script_dir, 'firebase-key.json')
    if os.path.exists(local_key_path):
        print(f"Using Firebase key from functions directory: {local_key_path}")
        return local_key_path

    # 3. Check parent directory's firebase folder
    parent_dir = os.path.dirname(script_dir)  # Get parent of functions/
    firebase_dir_path = os.path.join(parent_dir, 'firebase', 'firebase-key.json')
    if os.path.exists(firebase_dir_path):
        print(f"Using Firebase key from parent's firebase directory: {firebase_dir_path}")
        return firebase_dir_path

    # 4. Check for firebase-key.json in parent directory
    parent_key_path = os.path.join(parent_dir, 'firebase-key.json')
    if os.path.exists(parent_key_path):
        print(f"Using Firebase key from parent directory: {parent_key_path}")
        return parent_key_path

    raise FileNotFoundError(
        f"Could not find firebase-key.json in any location. Searched:\n"
        f"- Environment variable: {key_path_env}\n"
        f"- Functions directory: {local_key_path}\n"
        f"- Parent's firebase/: {firebase_dir_path}\n"
        f"- Parent directory: {parent_key_path}"
    )

try:
    key_path = find_firebase_key()
    app_initialized = False
    try:
        get_app()
        print("Firebase Admin already initialized.")
        app_initialized = True
    except ValueError:
        print("Firebase Admin not initialized yet.")
        pass

    if not app_initialized:
        if key_path:
            cred = credentials.Certificate(key_path)
            initialize_app(cred)
            print(f"Initialized Firebase Admin with key: {key_path}")
        elif IS_FIREBASE:
            initialize_app()
            print("Initialized Firebase Admin using default environment credentials.")
        else:
            print("Warning: Firebase key not found and not in Firebase environment. Firestore unavailable.", file=sys.stderr)
    
    if app_initialized or key_path or IS_FIREBASE:
        db = firestore.client()
        if db:
            print("Firestore client obtained successfully.")
        else:
            print("Warning: Failed to obtain Firestore client even after initialization attempt.", file=sys.stderr)

except Exception as e:
    print(f"CRITICAL Error during Firebase Admin initialization: {e}", file=sys.stderr)
    db = None

# Configuration management
@lru_cache()
def get_config():
    """Get configuration using os.getenv for both local and Firebase"""
    if IS_FIREBASE:
        print("Loading config using os.getenv (Firebase environment)")
        # Firebase Functions V2 automatically loads `firebase functions:config:set` 
        # values into environment variables, converting keys like `api.openai_key`
        # to `API_OPENAI_KEY`.
        openai_api_key = os.getenv('API_OPENAI_KEY')
        gemini_api_key = os.getenv('API_GEMINI_KEY')
        jwt_secret = os.getenv('JWT_SECRET')
        server_port = int(os.getenv('SERVER_PORT', '8000')) # Default if not set in config
        server_host = os.getenv('SERVER_HOST', '0.0.0.0') # Default if not set
        jwt_expiration_minutes = int(os.getenv('JWT_EXPIRATION_MINUTES', '60')) # Default if not set
    else:
        # Local development uses .env file loaded by dotenv
        print("Loading config from local .env file using os.getenv")
        openai_api_key = os.getenv('OPENAI_API_KEY') # Standard name for .env
        gemini_api_key = os.getenv('GOOGLE_GEMINI_API_KEY') # Standard name for .env
        jwt_secret = os.getenv('JWT_SECRET')
        server_port = int(os.getenv('PORT', '8000')) # Local often uses PORT
        server_host = os.getenv('HOST', '0.0.0.0')
        jwt_expiration_minutes = int(os.getenv('JWT_EXPIRATION_MINUTES', '60'))

    # --- Logging --- 
    # Use consistent logging regardless of environment
    env_type = "Firebase" if IS_FIREBASE else "Local"
    print(f"{env_type} Env Config: API_OPENAI_KEY retrieved: {'present' if openai_api_key else 'MISSING'}", file=sys.stderr)
    print(f"{env_type} Env Config: API_GEMINI_KEY retrieved: {'present' if gemini_api_key else 'MISSING'}", file=sys.stderr)
    print(f"{env_type} Env Config: JWT_SECRET retrieved: {'present' if jwt_secret else 'MISSING'}", file=sys.stderr)
    print(f"{env_type} Env Config: SERVER_PORT retrieved: {server_port}", file=sys.stderr)
    print(f"{env_type} Env Config: SERVER_HOST retrieved: {server_host}", file=sys.stderr)
    print(f"{env_type} Env Config: JWT_EXPIRATION_MINUTES retrieved: {jwt_expiration_minutes}", file=sys.stderr)

    # --- Check JWT Secret --- (Crucial check)
    if not jwt_secret:
        print(f"CRITICAL ERROR in get_config ({env_type}): JWT_SECRET is missing! Check environment variables / Firebase config.", file=sys.stderr)
        # In a real scenario, you might raise an error or prevent startup
        # raise ValueError("JWT_SECRET is required but not found")

    return {
        'openai_api_key': openai_api_key,
        'gemini_api_key': gemini_api_key,
        'server_port': server_port,
        'server_host': server_host,
        'jwt_secret': jwt_secret,
        'jwt_expiration_minutes': jwt_expiration_minutes
    }

# JWT Configuration
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

router = APIRouter()
security = HTTPBearer()

class MessageQueue:
    def __init__(self):
        self.messages_ref = db.collection('messages')
    
    async def push_message(self, target_id: str, message: dict):
        """Push a message to the target's queue"""
        # Add timestamp and ensure message is a dict
        if not isinstance(message, dict):
            message = {"content": str(message)}
        message["timestamp"] = datetime.utcnow().isoformat()
        
        # Get reference to the queue collection
        queue_ref = self.messages_ref.document(target_id).collection('queue')
        
        # Create a new document reference with auto-generated ID
        doc_ref = queue_ref.document()
        
        # Add the document ID to the message
        message["id"] = doc_ref.id
        
        # Run Firestore operations in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Use set instead of add to use our generated ID
        await loop.run_in_executor(None, lambda: doc_ref.set(message))
        print(f"Pushed message {doc_ref.id} to {target_id}'s queue")

        # Cleanup: Keep only the newest 100 messages
        # Run cleanup in thread too
        docs_stream = await loop.run_in_executor(None, lambda:
            queue_ref.order_by('timestamp', direction=firestore.Query.ASCENDING).stream()
        )
        docs_list = await loop.run_in_executor(None, lambda: list(docs_stream))
        total_docs = len(docs_list)

        if total_docs > 100:
            num_to_delete = total_docs - 100
            # Delete in thread
            for i in range(num_to_delete):
                await loop.run_in_executor(None, lambda: docs_list[i].reference.delete())
            print(f"Cleaned up {num_to_delete} old messages from {target_id}'s queue")

    async def get_messages(self, agent_id: str) -> list:
        """Get all messages for an agent, newest first"""
        messages = []
        try:
            # Run Firestore operations in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            msg_stream = await loop.run_in_executor(None, lambda: 
                self.messages_ref.document(agent_id).collection('queue')
                .order_by('timestamp', direction=firestore.Query.DESCENDING)
                .limit(10)
                .stream()
            )
            
            # Convert stream to list and process documents in the thread
            def process_docs():
                docs = []
                for doc in msg_stream:
                    msg_data = doc.to_dict()
                    # Ensure ID is present (use document ID if not in data)
                    if 'id' not in msg_data:
                        msg_data['id'] = doc.id
                    docs.append(msg_data)
                return docs
                
            messages = await loop.run_in_executor(None, process_docs)
            return messages
                
        except Exception as e:
            print(f"Error getting messages for {agent_id}: {e}")
            return []

    async def delete_message(self, target_id: str, message_id: str):
        """Delete a message from the target's queue"""
        try:
            # Run Firestore operations in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: 
                self.messages_ref.document(target_id).collection('queue')
                .document(message_id).delete()
            )
            print(f"Deleted message {message_id} from {target_id}'s queue")
        except Exception as e:
            print(f"Error deleting message {message_id}: {e}")
            raise e

    async def acknowledge_message(self, target_id: str, message_id: str):
        """Mark a message as acknowledged"""
        try:
            # Run Firestore operations in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda:
                self.messages_ref.document(target_id).collection('queue')
                .document(message_id).update({
                    'acknowledged': True,
                    'acknowledged_at': datetime.utcnow().isoformat()
                })
            )
            print(f"Marked message {message_id} as acknowledged in {target_id}'s queue")
        except Exception as e:
            print(f"Error acknowledging message {message_id}: {e}")
            raise e

class AgentRegistry:
    def __init__(self, db):
        self.agents_ref = db.collection('agents')

    async def register(self, agent_id: str, info: dict):
        """Register an agent asynchronously"""
        try:
            agent_data = {
                'info': info,
                'registered_at': datetime.utcnow().isoformat(),
                'last_heartbeat': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat()  # Keep this for backward compatibility
            }
            # Run Firestore operations in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, 
                lambda: self.agents_ref.document(agent_id).set(agent_data)
            )
            print(f"Agent {agent_id} registered successfully")
            return agent_id
        except Exception as e:
            print(f"Error registering agent {agent_id}: {e}")
            raise e

    async def get_agent_info(self, agent_id: str):
        """Get agent info asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(None, lambda: self.agents_ref.document(agent_id).get())
            if doc.exists:
                return doc.to_dict().get('info')
            return None
        except Exception as e:
            print(f"Error getting agent info for {agent_id}: {e}")
            return None

    async def heartbeat(self, agent_id: str):
        """Update agent's heartbeat asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: 
                self.agents_ref.document(agent_id).update({
                    'last_heartbeat': datetime.utcnow().isoformat(),
                    'last_seen': datetime.utcnow().isoformat()
                })
            )
        except Exception as e:
            print(f"Error updating heartbeat for {agent_id}: {e}")

    async def list_agents(self):
        """List all agents asynchronously"""
        try:
            loop = asyncio.get_event_loop()
            docs = await loop.run_in_executor(None, lambda: list(self.agents_ref.stream()))
            return [{"id": doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"Error listing agents: {e}")
            return []

# Initialize services
message_queue = MessageQueue()
agent_registry = AgentRegistry(db)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        print(f"Verifying token: {credentials.credentials[:10]}...")  # Only print first 10 chars for security
        # Get secret from config
        config = get_config()
        jwt_secret = config.get('jwt_secret')
        if not jwt_secret:
            print("ERROR in verify_token: JWT Secret not found in config")
            raise HTTPException(status_code=500, detail="Server configuration error: JWT secret missing.")

        token_data = jwt.decode(credentials.credentials, jwt_secret, algorithms=[JWT_ALGORITHM])
        print(f"Token decoded successfully: {token_data}")
        agent_id = token_data.get("agent_id")
        if not agent_id:
            print("Token missing agent_id")
            raise HTTPException(status_code=401, detail="Invalid token")
        return token_data
    except Exception as e:
        print(f"Token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/register")
async def register_agent(request: Request):
    """Register an agent"""
    try:
        data = await request.json()
        agent_id = data.get('agent_id')
        info = data.get('info', {})
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="Missing agent_id")
            
        # Register agent asynchronously
        await agent_registry.register(agent_id, info)
        
        # Generate token
        expiration = datetime.utcnow() + timedelta(minutes=int(os.getenv('JWT_EXPIRATION_MINUTES', '60')))
        token_data = {
            'agent_id': agent_id,
            'type': None,
            'exp': expiration
        }
        print(f"Generating token with data: {token_data}")
        token = jwt.encode(
            token_data,
            get_config().get('jwt_secret'), 
            algorithm=JWT_ALGORITHM
        )
        print(f"Generated token: {token[:10]}...")
        
        response = {
            'status': 'registered',
            'agent_id': agent_id,
            'token': token
        }
        return response
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message/{target_id}")
async def handle_message(
    target_id: str,
    request: Request,
    token_data: dict = Depends(verify_token)
):
    """Handle message delivery to target agent"""
    # Verify target exists
    target = await agent_registry.get_agent_info(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    message = await request.json()
    message["from"] = token_data["agent_id"]
    
    # Store message
    await message_queue.push_message(target_id, message)
    
    return {"status": "delivered"}

@router.post("/message/{agent_id}/acknowledge/{message_id}")
async def acknowledge_message(
    agent_id: str,
    message_id: str,
    request: Request,
    token_data: dict = Depends(verify_token)
):
    """Acknowledge message receipt and processing"""
    if token_data["agent_id"] != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    try:
        # Mark message as acknowledged
        await message_queue.acknowledge_message(agent_id, message_id)
        return {"status": "acknowledged", "message_id": message_id}
    except Exception as e:
        print(f"Error acknowledging message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/{agent_id}")
async def event_stream(
    request: Request,
    agent_id: str,
    token_data: dict = Depends(verify_token)
):
    """SSE endpoint for message delivery"""
    if token_data["agent_id"] != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    async def event_generator():
        last_yield_time = datetime.utcnow()
        last_heartbeat_time = datetime.utcnow()
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Send keep-alive every 30 seconds
                if (current_time - last_yield_time).total_seconds() > 30:
                    yield ": keep-alive\n\n"
                    last_yield_time = current_time
                    print(f"Sent keep-alive to {agent_id}")

                # Update heartbeat every minute
                if (current_time - last_heartbeat_time).total_seconds() > 60:
                    await agent_registry.heartbeat(agent_id)
                    last_heartbeat_time = current_time
                    print(f"Updated heartbeat for {agent_id}")

                # Get last_message_id from query params
                last_message_id = request.query_params.get('last_message_id')
                
                # Get latest messages
                messages = await message_queue.get_messages(agent_id)
                response_data = {
                    "messages": [],
                    "last_message_id": last_message_id
                }
                
                # Process new messages
                for msg in messages:
                    msg_id = msg.get("id")
                    if not msg_id:
                        continue
                        
                    # Check if this is a new message
                    if last_message_id is None or msg_id > last_message_id:
                        # Only include messages that haven't been acknowledged
                        if not msg.get("acknowledged", False):
                            response_data["messages"].append(msg)
                            response_data["last_message_id"] = msg_id
                
                # Send messages if we have any
                if response_data["messages"]:
                    print(f"Sending {len(response_data['messages'])} messages to {agent_id}")
                    yield f"data: {json.dumps(response_data)}\n\n"
                    last_yield_time = current_time
                
                # Short delay before checking for new messages
                await asyncio.sleep(0.1)  # Reduced from 0.5s to be more responsive
                
            except asyncio.CancelledError:
                print(f"Event stream for {agent_id} cancelled")
                break
            except Exception as e:
                print(f"Error in event stream for {agent_id}: {e}")
                await asyncio.sleep(1)  # Wait before retrying
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
            "Keep-Alive": "timeout=600"  # 10 minute timeout
        }
    )

@router.get("/agents")
async def list_agents(token_data: dict = Depends(verify_token)):
    """List all connected agents"""
    agents = await agent_registry.list_agents()
    return {"agents": agents}

if __name__ == "__main__":
    uvicorn.run(router, host=get_config()['server_host'], port=get_config()['server_port'])
