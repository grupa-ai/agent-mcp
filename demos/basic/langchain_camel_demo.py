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
import time

# MCP Components
from agent_mcp.mcp_agent import MCPAgent # Base class, maybe not needed directly
from agent_mcp.langchain_mcp_adapter import LangchainMCPAdapter
from agent_mcp.camel_mcp_adapter import CamelMCPAdapter
from agent_mcp.mcp_transport import HTTPTransport
from agent_mcp.mcp_decorator import mcp_agent, DEFAULT_MCP_SERVER

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

    # Adapters need to connect explicitly using the transport's connect method
    # The run method in the adapters likely expects the transport to be ready
    # Let's connect them before initializing the adapters that use them.
    # Although, the adapters themselves might call connect... let's see.
    # If the adapters call connect, we don't need to do it here.
    # Let's assume the adapters handle calling connect. 

    transport = HTTPTransport.from_url(DEFAULT_MCP_SERVER)

    # Initialize Adapters
    logger.info("Initializing Adapters...")
    langchain_adapter = LangchainMCPAdapter(
        name=LANGCHAIN_AGENT_NAME,
        agent_executor=langchain_executor,
        transport=transport,
        system_message=f"""I am the {LANGCHAIN_AGENT_NAME}. Let's have focused discussion about AI, multi-agent systems, and multi-agent collaboration."""
    )

    camel_adapter = CamelMCPAdapter(
        name=CAMEL_AGENT_NAME,
        transport=transport,
        camel_agent=camel_chat_agent,
        system_message=f"""I am the {CAMEL_AGENT_NAME}. Engage in substantive dialogue about AI agents."""
    )

    # Helper function to register an agent and extract token
    import json
    async def register_and_get_token(agent, agent_name):
        logger.info(f"Registering {agent_name}...")
        try:
            registration = await transport.register_agent(agent)
            body = json.loads(registration.get('body', '{}'))
            token = body.get('token')
            if token:
                logger.info(f"Registration successful for {agent_name}")
                return token
            logger.error(f"No token in response: {body}")
        except Exception as e:
            logger.error(f"Registration error for {agent_name}: {e}")
        return None

    # Register agents and get tokens
    langchain_token = await register_and_get_token(langchain_adapter, LANGCHAIN_AGENT_NAME)
    camel_token = await register_and_get_token(camel_adapter, CAMEL_AGENT_NAME)
    
    if not (langchain_token and camel_token):
        logger.error("Failed to register one or both agents")
        return

    # Now connect with both agent_name and token parameters
    await transport.connect(agent_name=LANGCHAIN_AGENT_NAME, token=langchain_token)
    await transport.connect(agent_name=CAMEL_AGENT_NAME, token=camel_token)

    # Start Adapters in background tasks
    lc_task = asyncio.create_task(langchain_adapter.run(), name=f"{LANGCHAIN_AGENT_NAME}_run")
    camel_task = asyncio.create_task(camel_adapter.run(), name=f"{CAMEL_AGENT_NAME}_run")

    # Allow time for adapters to fully start their loops
    logger.info("Waiting for adapters to initialize loops (2s)...")
    await asyncio.sleep(2)
    logger.info("Adapters should be running.")

    # --- Initiate Conversation ---
    initial_task_id = f"conv_start_{uuid.uuid4()}"
    initial_message_content = """Let's explore multi-agent coordination patterns through 3-5 focused exchanges. \
Please aim to: \
1. Identify key challenges\
2. Discuss 2-3 solutions  \
3. Propose conclusion when we've covered substantive ground"""

    initial_task = {
        "type": "task",
        "task_id": initial_task_id,
        "description": initial_message_content,
        "sender": LANGCHAIN_AGENT_NAME, # Langchain starts
        "reply_to": CAMEL_AGENT_NAME # Send responder as CamelAgent
    }

    # Replace conversation timer with hybrid limits
    MAX_DURATION = 60  # seconds (1 minute max)
    MAX_TURNS = 10
    TERMINATION_PHRASES = [
        "wrap up this discussion", 
        "finalize our discussion",
        "conclusion reached",
        "summary of key points"
    ]

    try:
        logger.info(f"[{LANGCHAIN_AGENT_NAME}] Sending initial message to {CAMEL_AGENT_NAME}...")
        await transport.send_message(target=CAMEL_AGENT_NAME, message=initial_task)

        start_time = time.monotonic()
        turn_count = 0

        while (time.monotonic() - start_time) < MAX_DURATION and turn_count < MAX_TURNS:
            try:
                msg, message_id = await asyncio.wait_for(transport.receive_message(), timeout=15)
                if msg:
                    content = msg.get('content', {}).get('text', '').lower()
                    if any(phrase in content for phrase in TERMINATION_PHRASES):
                        logger.info("Natural conversation conclusion detected")
                        break
                    turn_count += 1
            except asyncio.TimeoutError:
                logger.info("No message received in 15 seconds")
                break

        logger.info(f"Conversation ended after {turn_count} turns")
    except Exception as e:
        logger.error(f"An error occurred during conversation initiation or waiting: {e}", exc_info=True)

    finally: 
        logger.info("Initiating cleanup sequence...")
        
        # Cancel agent tasks first
        lc_task.cancel()
        camel_task.cancel()
        
        # Stop transport before awaiting
        await transport.stop()
        
        # Then await tasks
        await asyncio.gather(lc_task, camel_task, return_exceptions=True)
        
        # Finally disconnect transport
        await transport.disconnect()
        logger.info("Cleanup completed successfully")
        logger.info("Demo finished.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user.")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}", exc_info=True) 