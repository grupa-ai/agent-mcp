"""
Demo showcasing LangchainMCPAdapter and CamelMCPAdapter.

This script initializes one agent of each type, starts their adapters,
and sends a simple task to each via the configured MCP transport.
While langchain uses chatopenai
Camel uses camel.agents.ChatAgent and ModelFactory.create to create a model instance.
Both different frameworks for building agents.
Communication is done via MCP.
Check the logs to see the agents processing the tasks.
"""

import asyncio
import os
import logging
import uuid
from dotenv import load_dotenv
from typing import Dict, Any

# MCP Components
from agent_mcp.mcp_agent import MCPAgent # Base class, maybe not needed directly
from agent_mcp.langchain_mcp_adapter import LangchainMCPAdapter
from agent_mcp.camel_mcp_adapter import CamelMCPAdapter
# Remove Firestore import
# from agent_mcp.mcp_transport import FirestoreMCPTransport
# Import the base transport class for inheritance
from agent_mcp.mcp_transport import MCPTransport

# Langchain Components
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool # Import the tool decorator

# Camel AI Components
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelType, ModelPlatformType
from camel.configs import ChatGPTConfig

# Load environment variables (.env file)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
LANGCHAIN_AGENT_NAME = "LangchainDemoAgent"
CAMEL_AGENT_NAME = "CamelDemoAgent"
MODEL_NAME = "gpt-4o-mini" # Or "gpt-4", "gpt-3.5-turbo", etc.
SENDER_NAME = "DemoRunner" # Represents the entity sending initial tasks

# --- InMemoryTransport Implementation ---

class InMemoryTransport(MCPTransport):
    """A simple in-memory transport for local agent communication."""
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._agent_names: Dict[asyncio.Queue, str] = {} # Map queue back to agent name for receive
        self._message_store: Dict[str, Dict[str, Any]] = {} # message_id -> message content
        self._lock = asyncio.Lock()
        logger.info("InMemoryTransport initialized.")

    async def connect(self, agent_name: str):
        """Register an agent and create its message queue."""
        async with self._lock:
            if agent_name not in self._queues:
                queue = asyncio.Queue()
                self._queues[agent_name] = queue
                self._agent_names[queue] = agent_name
                logger.info(f"[InMemoryTransport] Agent '{agent_name}' connected.")
            else:
                logger.warning(f"[InMemoryTransport] Agent '{agent_name}' already connected.")

    async def disconnect(self, agent_name: str):
        """Unregister an agent and remove its queue."""
        async with self._lock:
            if agent_name in self._queues:
                queue = self._queues.pop(agent_name)
                del self._agent_names[queue]
                # Optionally clear any remaining messages in the queue?
                logger.info(f"[InMemoryTransport] Agent '{agent_name}' disconnected.")
            else:
                logger.warning(f"[InMemoryTransport] Agent '{agent_name}' not found for disconnect.")

    async def send_message(self, target: str, message: Dict[str, Any]):
        """Send a message to a target agent's queue."""
        async with self._lock:
            if target in self._queues:
                msg_id = f"mem_{uuid.uuid4()}"
                # Store the message content associated with the ID
                self._message_store[msg_id] = message.copy()
                # Put the ID onto the target queue
                await self._queues[target].put(msg_id)
                sender = message.get('sender', 'UnknownSender')
                logger.info(f"[InMemoryTransport] Message queued for '{target}' from '{sender}'. ID: {msg_id}. Content: {message}")
                return {"status": "queued", "message_id": msg_id}
            else:
                logger.error(f"[InMemoryTransport] Target agent '{target}' not connected. Cannot send message.")
                return {"status": "error", "message": f"Target agent '{target}' not found"}

    async def receive_message(self, agent_name: str):
        """Receive a message ID from the agent's queue and return the message content."""
        if agent_name not in self._queues:
            logger.error(f"[InMemoryTransport] Agent '{agent_name}' not connected. Cannot receive.")
            # Wait indefinitely or raise error? Let's wait shortly and return None
            await asyncio.sleep(0.1)
            return None, None

        queue = self._queues[agent_name]
        try:
            # Wait for a message ID with a timeout to prevent hanging forever if no message arrives
            # Or maybe adapters handle timeout? Let's wait indefinitely for now.
            logger.debug(f"[InMemoryTransport] Agent '{agent_name}' waiting for message...")
            msg_id = await queue.get()
            queue.task_done() # Mark task as done for the queue

            async with self._lock:
                message_content = self._message_store.get(msg_id)

            if message_content:
                logger.info(f"[InMemoryTransport] Agent '{agent_name}' received message ID '{msg_id}'. Content: {message_content}")
                return message_content, msg_id
            else:
                logger.error(f"[InMemoryTransport] Agent '{agent_name}' received unknown message ID '{msg_id}'.")
                return None, None

        except asyncio.CancelledError:
            logger.info(f"[InMemoryTransport] Receive task for '{agent_name}' cancelled.")
            return None, None
        except Exception as e:
             logger.error(f"[InMemoryTransport] Error receiving message for '{agent_name}': {e}", exc_info=True)
             return None, None


    async def acknowledge_message(self, agent_id: str, message_id: str):
        """Acknowledge receipt/processing of a message (removes from store)."""
        async with self._lock:
            if message_id in self._message_store:
                del self._message_store[message_id]
                logger.info(f"[InMemoryTransport] Message '{message_id}' acknowledged by agent '{agent_id}'.")
            else:
                logger.warning(f"[InMemoryTransport] Message '{message_id}' not found for acknowledgement by agent '{agent_id}'.")


# --- Agent Setup ---

# 1. Langchain Agent Setup
def setup_langchain_agent():
    logger.info("Setting up Langchain agent...")
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.7, api_key=os.getenv("OPENAI_API_KEY"))

    # Simple prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant called {agent_name}."),
        ("user", "{input}"),
        # Placeholder for agent scratchpad (required by create_openai_functions_agent)
        ("placeholder", "{agent_scratchpad}"),
    ])

    # Define a dummy tool to satisfy the OpenAI functions agent requirement
    @tool
    def dummy_tool() -> str:
        """A placeholder tool that does nothing."""
        return "This tool does nothing."

    # Add the dummy tool to the list
    tools = [dummy_tool]

    # Create the agent logic
    agent = create_openai_functions_agent(llm, tools, prompt)

    # Create the executor
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True) # Set verbose=True for Langchain logs
    logger.info("Langchain agent setup complete.")
    return agent_executor

# 2. Camel AI Agent Setup
def setup_camel_agent():
    logger.info("Setting up Camel AI agent...")
    # Ensure API key is available for Camel's model factory
    if not os.getenv("OPENAI_API_KEY"):
         raise ValueError("OPENAI_API_KEY must be set for Camel AI agent.")

    # Use Camel's ModelFactory
    # Note: Camel might need specific model type enums, adjust if needed
    try:
        # Find the appropriate ModelType enum for the model name
        camel_model_type = getattr(ModelType, MODEL_NAME.upper().replace("-", "_"), None)
        if camel_model_type is None:
             # Fallback or error - let's try a default
             logger.warning(f"Camel ModelType for '{MODEL_NAME}' not found directly, using GPT_4O_MINI as fallback.")
             camel_model_type = ModelType.GPT_4O_MINI # Adjust as needed

        # Specify the platform (OpenAI in this case)
        model_platform = ModelPlatformType.OPENAI

        # Provide platform, type, and basic config
        model_instance = ModelFactory.create(
            model_platform=model_platform,
            model_type=camel_model_type,
            model_config_dict=ChatGPTConfig().as_dict() # Add config dict
        )
    except Exception as e:
        logger.error(f"Failed to create Camel model: {e}. Ensure API keys are set and model type is supported.")
        raise

    # Create Camel ChatAgent
    system_prompt = "You are a creative AI assistant called {agent_name}, skilled in writing poetry."
    camel_agent = ChatAgent(system_message=system_prompt, model=model_instance)
    logger.info("Camel AI agent setup complete.")
    return camel_agent

# --- Main Execution ---

async def main():
    logger.info("Starting Langchain & Camel Adapters Demo...")

    # Ensure API Key is present
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("FATAL: OPENAI_API_KEY environment variable not set.")
        print("\nPlease set your OPENAI_API_KEY in a .env file or environment variables.\n")
        return

    # Initialize components
    langchain_executor = setup_langchain_agent()
    camel_chat_agent = setup_camel_agent()

    # Initialize Transport (Using InMemoryTransport)
    logger.info("Initializing InMemoryTransport...")
    # Create ONE instance to be shared by all adapters in this process
    transport = InMemoryTransport()

    # Adapters need to connect explicitly using the transport's connect method
    # The run method in the adapters likely expects the transport to be ready
    # Let's connect them before initializing the adapters that use them.
    # Although, the adapters themselves might call connect... let's see.
    # If the adapters call connect, we don't need to do it here.
    # Let's assume the adapters handle calling connect.

    # Initialize Adapters
    logger.info("Initializing Adapters...")
    langchain_adapter = LangchainMCPAdapter(
        name=LANGCHAIN_AGENT_NAME,
        agent_executor=langchain_executor,
        transport=transport, # Pass the shared transport instance
        system_message=f"I am the {LANGCHAIN_AGENT_NAME} adapter." # Optional: Adapter specific message
    )

    camel_adapter = CamelMCPAdapter(
        name=CAMEL_AGENT_NAME,
        camel_agent=camel_chat_agent,
        transport=transport, # Pass the shared transport instance
        system_message=f"I am the {CAMEL_AGENT_NAME} adapter. lets have a conversation about agents and their capabilities." # Optional: Adapter specific message
    )

    # Explicitly connect agents to the InMemoryTransport
    logger.info(f"Connecting {LANGCHAIN_AGENT_NAME} to transport...")
    await transport.connect(LANGCHAIN_AGENT_NAME)
    logger.info(f"Connecting {CAMEL_AGENT_NAME} to transport...")
    await transport.connect(CAMEL_AGENT_NAME)
    logger.info("Agents connected to transport.")

    # Start Adapters in background tasks
    lc_task = asyncio.create_task(langchain_adapter.run(), name=f"{LANGCHAIN_AGENT_NAME}_run")
    camel_task = asyncio.create_task(camel_adapter.run(), name=f"{CAMEL_AGENT_NAME}_run")

    # Allow time for adapters to fully start their loops
    logger.info("Waiting for adapters to initialize loops (2s)...")
    await asyncio.sleep(2)
    logger.info("Adapters should be running.")

    # --- Initiate Conversation ---
    initial_task_id = f"conv_start_{uuid.uuid4()}"
    initial_message_content = (
        f"Hello {CAMEL_AGENT_NAME}, I am {LANGCHAIN_AGENT_NAME}. "
        f"Let's have a brief chat about the challenges of building multi-agent systems."
    )

    initial_task = {
        "type": "task",
        "task_id": initial_task_id,
        "description": initial_message_content,
        "sender": LANGCHAIN_AGENT_NAME, # Langchain starts
        "reply_to": LANGCHAIN_AGENT_NAME # Camel should reply back to Langchain
    }

    try:
        logger.info(f"[{LANGCHAIN_AGENT_NAME}] Sending initial message to {CAMEL_AGENT_NAME}...")
        await transport.send_message(target=CAMEL_AGENT_NAME, message=initial_task)

        # Let the conversation run for a while (agents handle turns internally)
        conversation_duration = 60 # seconds
        logger.info(f"Conversation initiated. Waiting {conversation_duration} seconds for interaction (check logs)...")
        await asyncio.sleep(conversation_duration)
        logger.info("Finished conversation time.")

    except Exception as e:
        logger.error(f"An error occurred during conversation initiation or waiting: {e}", exc_info=True)

    finally:
        # Stop adapters and transport
        logger.info("Shutting down adapters...")
        await langchain_adapter.stop()
        await camel_adapter.stop()

        # Wait for run tasks to complete cancellation
        logger.info("Waiting for adapter tasks to finish...")
        await asyncio.gather(lc_task, camel_task, return_exceptions=True)

        # No explicit transport disconnect needed for InMemory, but good practice if base class had it
        # logger.info("Disconnecting transport...")
        # await transport.disconnect(LANGCHAIN_AGENT_NAME) # Adapters might do this in stop()
        # await transport.disconnect(CAMEL_AGENT_NAME)
        logger.info("Demo finished.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user.")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}", exc_info=True) 