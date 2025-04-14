"""Example demonstrating how to create a simple MCP-compatible email agent."""

import os
import asyncio
from dotenv import load_dotenv
from email_agent import EmailAgent

# Load environment variables
load_dotenv()

async def demonstrate_email_agent():
    # Create and initialize the email agent
    email_agent = EmailAgent()
    
    # Connect to the MCP network
    await email_agent.connect()
    print("Email agent is connected and ready to receive tasks")
    

    # Start message and task processors
    email_agent.run()

    try:
        # Wait for interrupt - the adapter handles message processing
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down email agent...")
        await email_agent.disconnect()

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = [
        "EMAIL_ADDRESS",
        "EMAIL_PASSWORD",
        "SMTP_SERVER",
        "SMTP_PORT"
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them in your .env file")
    else:
        print("Starting email agent...")
        asyncio.run(demonstrate_email_agent())