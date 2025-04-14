"""
Super simple example of two agents chatting through the hosted server.
Just run this file and watch them talk!
"""

import asyncio
import os
import logging
from typing import TypedDict, Optional, Union
from dotenv import load_dotenv
import autogen
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from agent_mcp import mcp_agent
from agent_mcp.mcp_agent import MCPAgent
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Server URL
#server_url = os.getenv('MCP_SERVER_URL', 'https://mcp-server-ixlfhxquwq-ew.a.run.app')
#print(f"Using MCP Server: {server_url}")

# --- Agent Definitions ---

# Autogen Agent with MCP
@mcp_agent(mcp_id="AutoGen_Alice")
class AutogenAgent(autogen.ConversableAgent):
    def __init__(self, name="AutoGen_Alice", **kwargs):
        llm_config = {
            "config_list": [{
                "model": "gpt-4",
                "api_key": os.getenv("OPENAI_API_KEY")
            }],
            "temperature": 0.7
        }
        super().__init__(
            name=name,
            llm_config=llm_config,
            system_message="You are Alice. Keep responses short. End the conversation if Bob says 'goodbye' or after 5 exchanges.",
            human_input_mode="NEVER",
            **kwargs
        )
        self.message_count = 0
        
    async def process_received_message(self, message, sender):
        """Process received message and generate reply using Autogen's capabilities"""
        # Extract message content properly
        message_text = self._extract_message_text(message)
        
        # Ensure we have valid content
        if not message_text:
            logger.warning(f"Invalid message received: {message}")
            return None
            
        # Check for end conditions
        self.message_count += 1
        if self.message_count >= 5:
            # Generate a farewell message
            reply = await self.a_generate_reply(
                messages=[{"role": "user", "content": "Generate a friendly goodbye message as we've reached the end of our conversation."}],
            )
            if isinstance(reply, dict):
                reply = reply.get('content', '')
            return {"content": {"text": str(reply)}}
            
        # Use Autogen's built-in reply generation
        reply = await self.a_generate_reply(
            messages=[{
                "role": "system", 
                "content": "You are having a friendly conversation. Respond naturally to the user's message."
            }, {
                "role": "user", 
                "content": message_text
            }],
        )
        print("Message from Autogen: ", reply)
        if isinstance(reply, dict):
            reply = reply.get('content', '')
        return {"content": {"text": str(reply)}}
    
    def _extract_message_text(self, message: Union[dict, tuple]) -> str:
        """Extract text content from message, handling different message formats"""
        logger.info(f"Processing message: {message}")
        
        # Handle tuple format
        if isinstance(message, tuple):
            message = message[0]  # Extract message dict from tuple
            logger.info(f"Extracted message from tuple: {message}")
            
        # Handle dict format
        if isinstance(message, dict):
            # Check for nested content structure
            if 'content' in message:
                content = message['content']
                if isinstance(content, dict):
                    # Handle nested content with text field
                    if 'text' in content:
                        text = content['text']
                        logger.info(f"Extracted text from nested content: {text}")
                        return text
                    else:
                        logger.warning(f"Content dict missing 'text' field: {content}")
                        return str(content)
                elif isinstance(content, str):
                    # Handle direct string content
                    logger.info(f"Extracted direct string content: {content}")
                    return content
                else:
                    logger.warning(f"Unexpected content type: {type(content)}")
                    return str(content)
            else:
                logger.warning(f"Message missing 'content' field: {message}")
                return str(message)
                
        logger.warning(f"Unexpected message format: {message}")
        return str(message)

# LangGraph Agent with MCP
class ChatState(TypedDict):
    """State definition for chat"""
    messages: list[dict]
    current_message: str
    response: Optional[str]
    message_count: int

@mcp_agent(mcp_id="LangGraph_Bob")
class LangGraphAgent:
    """LangGraph-based agent with MCP integration"""
    def __init__(self, name: str):
        self.name = name
        self.message_count = 0
        
        # Initialize LLM
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.llm = ChatOpenAI(temperature=0.7)
        
        # Create chat prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are Bob, a friendly AI assistant having a conversation. Respond naturally and engagingly to the user's messages."),
            ("user", "{message}")
        ])
        
        # Create LangGraph workflow
        workflow = StateGraph(ChatState)
        
        # Add processing node
        workflow.add_node("process", self._process_message)
        
        # Set entry point and connect nodes
        workflow.add_edge(START, "process")
        workflow.add_edge("process", END)
        
        # Compile the graph
        self.app = workflow.compile()

    def _process_message(self, state: ChatState) -> ChatState:
        """Process a message in the chat using LLM"""
        # Get current message from state
        message = state["current_message"]
        
        # Generate response using LLM
        chain = self.prompt | self.llm
        response = chain.invoke({"message": message})
        print("Message from LangGraph: ", response)
        # Extract response content
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Update state with generated response
        return {
            "messages": state.get("messages", []) + [{"role": "assistant", "content": response_text}],
            "current_message": message,
            "response": response_text,
            "message_count": state.get("message_count", 0) + 1
        }

    async def process_received_message(self, message, sender):
        """Process received message through LangGraph state machine"""
        # Extract message content properly
        message_text = self._extract_message_text(message)
        
        if not message_text:
            logger.warning(f"Invalid message received: {message}")
            return None
            
        # Set initial state
        state = {
            "messages": [],
            "current_message": message_text,
            "message_count": 0,
            "response": None
        }
        
        # Process through LangGraph app
        try:
            # The app will run _process_message which updates the state
            # Use asynchronous invoke to avoid blocking the event loop
            result = await self.app.ainvoke(state) 
            
            # Get the response from the updated state
            response_text = result.get('response', '')
            if not response_text:
                logger.warning("No response generated by workflow")
                return None
                
            # Update message count
            self.message_count += 1
                
            # Return response in proper format
            return {
                "content": {
                    "text": response_text
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing message through workflow: {e}")
            return None
    
    def _extract_message_text(self, message: Union[dict, tuple]) -> str:
        """Extract text content from message, handling different message formats"""
        logger.info(f"Processing message: {message}")
        
        # Handle tuple format
        if isinstance(message, tuple):
            message = message[0]  # Extract message dict from tuple
            logger.info(f"Extracted message from tuple: {message}")
            
        # Handle dict format
        if isinstance(message, dict):
            # Check for nested content structure
            if 'content' in message:
                content = message['content']
                if isinstance(content, dict):
                    # Handle nested content with text field
                    if 'text' in content:
                        text = content['text']
                        logger.info(f"Extracted text from nested content: {text}")
                        return text
                    else:
                        logger.warning(f"Content dict missing 'text' field: {content}")
                        return str(content)
                elif isinstance(content, str):
                    # Handle direct string content
                    logger.info(f"Extracted direct string content: {content}")
                    return content
                else:
                    logger.warning(f"Unexpected content type: {type(content)}")
                    return str(content)
            else:
                logger.warning(f"Message missing 'content' field: {message}")
                return str(message)
                
        logger.warning(f"Unexpected message format: {message}")
        return str(message)

async def main():
    # Initialize agents
    alice = AutogenAgent()
    bob = LangGraphAgent("LangGraph_Bob")
    
    try:
        # Connect agents
        logger.info("Connecting agents...")
        await asyncio.gather(
            alice.connect(),
            bob.connect()
        )
        logger.info("Agents connected successfully.")
        
        # Clean up phase - acknowledge any old messages
        logger.info("Cleaning up old messages...")
        await asyncio.sleep(2)  # Wait for initial polling
        
        # Initial message
        current_sender = alice
        init_message = await alice.a_generate_reply(messages=[{
            "role": "user",
            "content": "generate a friendly greeting in a super duper casual way" 
        }])
        print("Initial message: ", init_message)
        current_receiver = bob
        message = {
            "content": {
                "text": init_message,
             }
        }
        
        processed_messages = set()  # Track processed message IDs
        message_count = 0  # Track total messages processed
        MAX_MESSAGES = 10  # Maximum number of messages before ending conversation
        
        # Conversation loop
        while True:
            try:
                if message_count >= MAX_MESSAGES:
                    logger.info("Maximum message count reached. Ending conversation.")
                    break
                    
                # Send message
                logger.info(f"[{current_sender.name}] Sending: {message}")
                await current_sender.send_message(target=current_receiver.name, message=message)
                
                # Wait for reply with timeout
                logger.info(f"[{current_receiver.name}] Waiting for reply...")
                received_msg = await current_receiver.receive_message() # Increased timeout
                
                if not received_msg:
                    logger.warning("No message received. Ending conversation.")
                    break
                
                # Process received message
                response = await current_receiver.process_received_message(received_msg, current_sender.name)
                
                # Check for valid response
                if not response or not isinstance(response, dict) or 'content' not in response:
                    logger.warning("Invalid response format. Ending conversation.")
                    break
                    
                # Check for goodbye messages
                content = response['content'].get('text', '').lower()
                if 'goodbye' in content:
                    logger.info("Goodbye message detected. Ending conversation.")
                    break
                        
                # Swap sender and receiver and update message
                current_sender, current_receiver = current_receiver, current_sender
                # Use the generated response as the next message
                message = response  # Use the full response object as the next message
                message_count += 1

            except Exception as e:
                logger.error(f"An error occurred: {e}", exc_info=True)
                break
                
    finally:
        # Disconnect agents
        logger.info("Disconnecting agents...")
        await asyncio.gather(
            alice.disconnect(),
            bob.disconnect(),
            return_exceptions=True
        )
        logger.info("Agents disconnected.")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in .env file.")
    asyncio.run(main())