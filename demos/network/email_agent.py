"""Simple Email Agent Example

This example shows how to create a simple email agent using just the @mcp_agent decorator.
The decorator automatically handles all the MCP communication functionality.
"""

import os
import smtplib
import logging
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from agent_mcp import mcp_agent
from agent_mcp.langgraph_mcp_adapter import LangGraphMCPAdapter
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
print("Email Agent is starting...")


@mcp_agent(mcp_id="EmailAgent")
class EmailAgent(LangGraphMCPAdapter):
    """An agent capable of sending emails through SMTP."""
    
    def __init__(self):
        """Initialize email agent with SMTP settings"""
        # Email configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        
        if not all([self.email_address, self.email_password]):
            logger.warning("Email credentials not found in environment variables")
            
        # Create workflow using dict for state
        workflow = StateGraph(dict)
        workflow.add_node("send_email", self.send_email)
        workflow.add_edge(START, "send_email")
        workflow.add_edge("send_email", END)
        
        # Initialize adapter with workflow but preserve transport
        transport = getattr(self, 'transport', None)
        super().__init__(name="EmailAgent", workflow=workflow, state_type=dict)
        if transport:
            self.transport = transport
    
    async def send_email(self, state_dict: dict):
        """Send an email using configured SMTP settings"""
        try:
            print("Email Agent is about to send email...")
            print(f"State dict received: {state_dict}")
            
            # Get the task message (could be in message or content field)
            task = state_dict.get('message') or state_dict.get('content')
            print(f"Task received: {task}")
            
            result = None
            if not all([self.email_address, self.email_password]):
                result = "Error: Email credentials not configured"
                return {"message": task, "result": result}
            
            # Extract content from task
            if isinstance(task, dict):
                if 'text' in task:
                    try:
                        content = json.loads(task['text'])
                    except json.JSONDecodeError:
                        content = task
                else:
                    content = task
            else:
                content = task
                
            print(f"Content after parsing: {content}")
            
            # Extract parameters
            params = content.get('email_params', content)
            to_address = params.get('to_address')
            subject = params.get('subject')
            body = params.get('body') or content.get('content')
            body = re.sub(r'^Subject:.*?\n', '', body, flags=re.IGNORECASE).strip()

            cc_address = params.get('cc_address')
            
            print(f"Extracted params: to={to_address}, subject={subject}, body={body}, cc={cc_address}")
            
            if not all([to_address, subject, body]):
                result = "Error: Missing required email parameters"
                logger.error(f"Missing email parameters. Got: {params}")
                return {"message": task, "result": result}
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to_address
            msg['Subject'] = subject
            
            if cc_address:
                msg['Cc'] = cc_address
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                
                # Send email
                recipients = [to_address]
                if cc_address:
                    recipients.append(cc_address)
                server.sendmail(self.email_address, recipients, msg.as_string())
                
            logger.info(f"Email sent successfully to {to_address}")
            result = "Email sent successfully"
            return {"message": task, "result": result}
            
        except Exception as e:
            result = f"Error sending email: {str(e)}"
            logger.error(f"Error sending email: {e}")
            return {"message": task, "result": result}