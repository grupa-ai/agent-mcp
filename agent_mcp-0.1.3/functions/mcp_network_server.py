"""
MCP Network Server - Central hub for agent communication.
"""

from fastapi import Request, Depends, HTTPException, APIRouter, Response
from fastapi.security import HTTPBearer
from fastapi.responses import StreamingResponse, JSONResponse
from firebase_admin import initialize_app, get_app, credentials
from firebase_admin import firestore 
import uvicorn
import asyncio
import time
from datetime import datetime, timedelta, timezone
#from google.cloud.firestore_v1.types.document import DocumentSnapshot
#from google.cloud._helpers import _datetime_to_pb_timestamp
from typing import Dict, Set, Any, Optional, Union
import json
import os
import sys
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from functools import lru_cache
from dotenv import load_dotenv
from utils import convert_timestamps_to_isoformat
import logging
from fastapi import Query
from pydantic import BaseModel
from typing import List

# Set up logging
logger = logging.getLogger(__name__)

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
    """Find and validate the Firebase key file location."""
    # The exact path that Firebase Functions emulator expects
    key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'firebase', 'firebase-key.json')
    print(f"Using key path: {key_path}")
    
    if not os.path.exists(key_path):
        raise FileNotFoundError(
            f"\nFirebase key not found at {key_path}\n"
            "Please ensure firebase-key.json exists in the functions/firebase/ directory.\n"
        )
    return key_path

try:
    # Check if we're running in Firebase Functions
    if IS_FIREBASE:
        print("Running in Firebase Functions environment")
        initialize_app()
        db = firestore.client()
        print("Initialized Firebase Admin using default credentials (sync client)")
    else:
        # Get the key path
        key_path = find_firebase_key()
            
        # Initialize Firebase with the key
        print(f"Initializing Firebase Admin with key: {key_path}")
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = key_path
        cred = credentials.Certificate(key_path)
        initialize_app(cred)
        db = firestore.client()
        print("Firestore client obtained successfully (sync client)")

except Exception as e:
    print(f"CRITICAL Error during Firebase Admin initialization: {e}", file=sys.stderr)
    print("Please ensure you have valid Firebase credentials set up.", file=sys.stderr)
    raise  # Re-raise to prevent starting with invalid credentials

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

    def push_message(self, target_id: str, message: dict):
        """Push a message to the target's queue"""
        try:
            # Always set timestamp to ensure consistency
            message['timestamp'] = datetime.utcnow().replace(tzinfo=timezone.utc)
            
            # Add acknowledged flag
            message['acknowledged'] = False

            # Create a new document reference with auto-generated ID
            queue_ref = self.messages_ref.document(target_id).collection('queue')
            doc_ref = queue_ref.document()
            message_id = doc_ref.id
            
            # Add the ID to the message before saving
            message['id'] = message_id
            
            # Save the message
            doc_ref.set(message)
            print(f"Pushed message {message_id} to {target_id}")
            return message_id
        except Exception as e:
            print(f"Error pushing message to {target_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error pushing message: {e}")

    def get_messages(self, agent_id: str, last_message_id: str = None) -> list:
        """Get all unacknowledged messages for an agent after the last_message_id"""
        messages = []
        try:
            print(f"\n====== FETCHING MESSAGES FOR {agent_id} ======")
            print(f"Last message ID: {last_message_id}")
            
            # Build the query
            query = self.messages_ref.document(agent_id).collection('queue')
            
            # Only get unacknowledged messages
            query = query.where('acknowledged', '==', False)
            
            # Order by timestamp descending to get newest first
            query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            # Get current time in UTC
            current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
            cutoff_time = current_time - timedelta(minutes=1)  # Only get messages from last 1 minute
            
            # Add timestamp filter to only get recent messages
            query = query.where('timestamp', '>', cutoff_time)
            
            # If we have a last_message_id, get the timestamp of that message
            if last_message_id:
                try:
                    # Correctly get the document from the collection reference
                    last_msg_ref = self.messages_ref.document(agent_id).collection('queue').document(last_message_id)
                    last_msg = last_msg_ref.get()
                    if last_msg.exists:
                        last_timestamp = last_msg.to_dict().get('timestamp')
                        if last_timestamp:
                            # Only get messages after the last one
                            query = query.where('timestamp', '>', last_timestamp)
                except Exception as e:
                    print(f"Error getting last message {last_message_id}: {e}")
            
            # Limit to 10 messages at a time
            query = query.limit(10)
            
            # Process documents
            for doc in query.stream():
                msg_data = doc.to_dict()
                msg_data['id'] = doc.id
                msg_data = convert_timestamps_to_isoformat(msg_data)
                messages.append(msg_data)
                
                # Log message details
                print(f"\n----- Message {msg_data['id']} -----")
                print(f"Type: {msg_data.get('type', 'unknown')}")
                print(f"Task ID: {msg_data.get('task_id', 'unknown')}")
                print(f"Acknowledged: {msg_data.get('acknowledged', False)}")
                print(f"Timestamp: {msg_data.get('timestamp', 'unknown')}")
                if 'content' in msg_data:
                    print(f"Content: {json.dumps(msg_data['content'], indent=2)}")
                if 'description' in msg_data:
                    print(f"Description: {msg_data['description']}")
                if 'reply_to' in msg_data:
                    print(f"Reply To: {msg_data['reply_to']}")
                print("-" * 40)
            
            print(f"Found {len(messages)} messages")
            print("====== END MESSAGES ======\n")
            return messages

        except Exception as e:
            print(f"Error getting messages for {agent_id}: {e}")
            return []

    def delete_message(self, target_id: str, message_id: str):
        """Delete a message from the target's queue"""
        try:
            # Use synchronous delete
            self.messages_ref.document(target_id).collection('queue').document(message_id).delete()
            print(f"Deleted message {message_id} for {target_id}")
        except Exception as e:
            print(f"Error deleting message {message_id} for {target_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting message: {e}")

    def acknowledge_message(self, target_id: str, message_id: str):
        """Mark a message as acknowledged"""
        try:
            # Use synchronous update
            doc_ref = self.messages_ref.document(target_id).collection('queue').document(message_id)
            doc_ref.update({'acknowledged': True, 'acknowledged_at': datetime.utcnow().replace(tzinfo=timezone.utc)}) # doc_ref.update({'acknowledged': True, 'acknowledged_at': firestore.SERVER_TIMESTAMP})
            print(f"Acknowledged message {message_id} for {target_id}")
        except Exception as e:
            print(f"Error acknowledging message {message_id} for {target_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error acknowledging message: {e}")


class AgentRegistry:
    def __init__(self, db):
        self.agents_ref = db.collection('agents')

    def register(self, agent_id: str, info: dict):
        """Register an agent"""
        try:
            agent_data = {
                'info': info,
                'registered_at': datetime.utcnow().isoformat(),
                'last_heartbeat': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat()  # Keep this for backward compatibility
            }
            # Run Firestore operations in a thread to avoid blocking
            self.agents_ref.document(agent_id).set(agent_data)
            print(f"Agent {agent_id} registered successfully")
            return agent_id
        except Exception as e:
            print(f"Error registering agent {agent_id}: {e}")
            raise e

    def get_agent_info(self, agent_id: str):
        """Get agent info"""
        try:
            doc = self.agents_ref.document(agent_id).get()
            if doc.exists:
                return doc.to_dict().get('info')
            return None
        except Exception as e:
            print(f"Error getting agent info for {agent_id}: {e}")
            return None

    def heartbeat(self, agent_id: str):
        """Update agent's heartbeat"""
        try:
            self.agents_ref.document(agent_id).update({
                'last_heartbeat': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"Error updating heartbeat for {agent_id}: {e}")

    def list_agents(self):
        """List all agents"""
        try:
            docs = self.agents_ref.stream()
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
        # Await request.json()
        data = await request.json()
        agent_id = data.get('agent_id')
        info = data.get('info', {})
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="Missing agent_id")
            
        # Register agent
        agent_registry.register(agent_id, info)
        
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
    target = agent_registry.get_agent_info(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Await request.json()
    message = await request.json()
    message["from"] = token_data["agent_id"]
    
    # Store message
    message_id = message_queue.push_message(target_id, message)
    
    return {"status": "delivered", "message_id": message_id}

@router.get("/messages/{agent_id}")
async def get_messages_endpoint(agent_id: str, last_message_id: Optional[str] = Query(None), token_data: dict = Depends(verify_token)):
    """Endpoint for clients to poll for new messages.

    Args:
        agent_id: The ID of the agent requesting messages.
        last_message_id: The ID of the last message the client received (optional).
        token_data: Decoded JWT token data.

    Returns:
        A list of new messages.
    
    Raises:
        HTTPException: 403 if token doesn't match agent_id.
        HTTPException: 500 if there's an error fetching messages.
    """
    # Verify the token belongs to the agent asking for messages
    if token_data["agent_id"] != agent_id:
        logger.warning(f"Auth Error: Token agent ({token_data['agent_id']}) mismatch with requested agent_id ({agent_id}) for polling")
        raise HTTPException(status_code=403, detail="Token does not match requested agent ID")
    
    logger.info(f"Polling request for {agent_id}. Last message ID: {last_message_id}")
    
    try:
        message_queue = MessageQueue() # Instantiate locally for the request
        # Run the synchronous Firestore call in a thread pool executor
        loop = asyncio.get_event_loop()
        messages = await loop.run_in_executor(
            None, # Use default executor
            message_queue.get_messages,
            agent_id,
            last_message_id
        )
        
        logger.info(f"Found {len(messages)} messages for {agent_id} after {last_message_id}")
        
        # Return empty list if no messages
        if not messages:
            logger.debug(f"No messages found for agent {agent_id}")
            return []
            
        # Unwrap Firestore documents into a consistent format
        formatted_messages = []
        for msg in messages:
            # Convert Firestore document to dict if needed
            msg_dict = msg.to_dict() if hasattr(msg, 'to_dict') else msg
            logger.info(f"Processing message for {agent_id}: {json.dumps(msg_dict, indent=2)}")
            
            # Skip invalid messages
            if not isinstance(msg_dict, dict):
                logger.warning(f"Skipping invalid message format for {agent_id}: {msg_dict}")
                continue
                
            # Get message ID
            msg_id = msg_dict.get('id')
            if not msg_id and hasattr(msg, 'id'):
                msg_id = msg.id
                logger.debug(f"Using Firestore document ID for message: {msg_id}")
            
            # Skip messages without ID
            if not msg_id:
                logger.warning(f"Skipping message without ID for {agent_id}: {msg_dict}")
                continue
                
            # Format message with required fields
            formatted_msg = {
                'id': msg_id,
                'type': msg_dict.get('type', 'message'),  # Default to 'message' type
                'content': msg_dict.get('content', {'text': 'No content provided'}),  # Always provide content
                'timestamp': msg_dict.get('timestamp', datetime.utcnow().isoformat()),  # Default to current time
                'from': msg_dict.get('from', 'unknown'),  # Default to unknown sender
            }
            
            # Include optional fields if present
            for field in ['task_id', 'description', 'reply_to', 'result']:
                if field in msg_dict:
                    formatted_msg[field] = msg_dict[field]
                    
            logger.info(f"Formatted message for {agent_id}: {json.dumps(formatted_msg, indent=2)}")
            formatted_messages.append(formatted_msg)
            
        return formatted_messages
    except Exception as e:
        logger.error(f"Error fetching messages for {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")

@router.post("/message/{agent_id}/acknowledge/{message_id}")
async def acknowledge_message(
    agent_id: str,
    message_id: str,
    request: Request,
    token_data: dict = Depends(verify_token)
):
    """Acknowledge message receipt and processing"""
    print(f"[{agent_id}] Received acknowledgment request for message {message_id}")
    
    if token_data["agent_id"] != agent_id:
        print(f"[{agent_id}] Authorization failed for message {message_id}. Token agent_id: {token_data['agent_id']}")
        raise HTTPException(status_code=403, detail="Not authorized")
        
    try:
        # Mark message as acknowledged
        print(f"[{agent_id}] Attempting to acknowledge message {message_id}")
        message_queue.acknowledge_message(agent_id, message_id)
        print(f"[{agent_id}] Successfully acknowledged message {message_id}")
        return {"status": "acknowledged", "message_id": message_id}
    except Exception as e:
        print(f"[{agent_id}] Error acknowledging message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents")
async def list_agents(token_data: dict = Depends(verify_token)):
    """List all connected agents"""
    agents = agent_registry.list_agents()
    return {"agents": agents}

if __name__ == "__main__":
    uvicorn.run(router, host=get_config()['server_host'], port=get_config()['server_port'])
