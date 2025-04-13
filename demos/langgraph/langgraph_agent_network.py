"""
LangGraph Agent Network Example using MCPNode.

This example demonstrates a network of agents built with LangGraph and the MCP protocol,
showing how to create a flexible agent network where multiple specialized agents can
collaborate and share context through a coordinator.
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional, cast, Callable

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
import langgraph.graph
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from openai import OpenAI

# Import our MCP implementation for LangGraph
from agent_mcp.mcp_langgraph import MCPNode, MCPReactAgent, create_mcp_langgraph

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)


def get_llm():
    """Get the OpenAI LLM wrapper that implements the langchain interface."""
    from langchain_openai import ChatOpenAI
    
    # Initialize with the newest model (gpt-4) which was released after your knowledge cutoff
    return ChatOpenAI(model="gpt-4", temperature=0.7)


class LangGraphAgentNetwork:
    """A network of LangGraph agents using MCP for communication and context sharing."""
    
    def __init__(self):
        """Initialize the agent network."""
        self.llm = get_llm()
        self.agents = {}
        self.network_id = str(uuid.uuid4())
        self.shared_workspace = {}
        self.message_history = []
        
        # Create the agent network
        self.create_network()
    
    def create_network(self):
        """Create all agents in the network and connect them."""
        # Create the coordinator agent
        coordinator = MCPReactAgent(
            name="Coordinator",
            system_message=(
                "You are the Coordinator agent responsible for managing communication "
                "and task assignment across the network. You should help users interact "
                "with specialized agents and facilitate collaboration."
            )
        )
        
        # Create specialized agents
        researcher = MCPReactAgent(
            name="Researcher",
            system_message=(
                "You are the Researcher agent specialized in gathering and synthesizing "
                "information. You excel at finding relevant data and organizing it into "
                "coherent summaries."
            )
        )
        
        analyst = MCPReactAgent(
            name="Analyst",
            system_message=(
                "You are the Analyst agent specialized in data analysis and interpretation. "
                "You can identify patterns, extract insights, and explain complex data in "
                "simple terms."
            )
        )
        
        planner = MCPReactAgent(
            name="Planner",
            system_message=(
                "You are the Planner agent specialized in strategic planning and task "
                "decomposition. You can break down complex problems into actionable steps."
            )
        )
        
        creative = MCPReactAgent(
            name="Creative",
            system_message=(
                "You are the Creative agent specialized in generating innovative ideas "
                "and creative content. You can think outside the box and provide unique "
                "perspectives on problems."
            )
        )
        
        # Add them to our agent dictionary
        self.agents = {
            "coordinator": coordinator,
            "researcher": researcher,
            "analyst": analyst,
            "planner": planner,
            "creative": creative
        }
        
        # Register custom tools for all agents
        self._register_network_tools()
        
        # Connect the agents (register each agent as a tool for others)
        self._connect_agents()
        
        # Share the workspace with all agents
        self._share_workspace()
    
    def _register_network_tools(self):
        """Register network-specific tools for all agents."""
        # Register tools for each agent
        for agent_id, agent in self.agents.items():
            # Tool to update the shared workspace
            def workspace_update(section: str, key: str, value: Any, agent_id=agent_id):
                """Update a section of the shared workspace."""
                self.update_workspace(section, key, value, from_agent=agent_id)
                return json.dumps({
                    "status": "success",
                    "message": f"Updated workspace: {section}/{key}"
                })
            
            # Tool to read from the shared workspace
            def workspace_get(section: str, key: Optional[str] = None, agent_id=agent_id):
                """Get data from the shared workspace."""
                if section not in self.shared_workspace:
                    return json.dumps({
                        "status": "error",
                        "message": f"Section '{section}' not found in workspace"
                    })
                
                if key is None:
                    return json.dumps({
                        "status": "success",
                        "data": self.shared_workspace[section]
                    })
                
                if key not in self.shared_workspace[section]:
                    return json.dumps({
                        "status": "error",
                        "message": f"Key '{key}' not found in section '{section}'"
                    })
                
                return json.dumps({
                    "status": "success",
                    "data": self.shared_workspace[section][key]
                })
            
            # Tool to send a message to the network
            def send_message(message: str, agent_id=agent_id):
                """Send a message to all agents in the network."""
                self.add_message(agent_id, message)
                return json.dumps({
                    "status": "success",
                    "message": "Message sent to the network"
                })
            
            # Tool to list all agents in the network
            def list_agents(agent_id=agent_id):
                """List all agents in the network."""
                agents_list = [
                    {"id": aid, "name": a.name}
                    for aid, a in self.agents.items()
                ]
                return json.dumps({
                    "status": "success",
                    "agents": agents_list
                })
            
            # Register the tools with the agent
            agent.register_custom_tool(
                "workspace_update",
                "Update a section of the shared workspace",
                workspace_update
            )
            
            agent.register_custom_tool(
                "workspace_get",
                "Get data from the shared workspace",
                workspace_get
            )
            
            agent.register_custom_tool(
                "send_message",
                "Send a message to all agents in the network",
                send_message
            )
            
            agent.register_custom_tool(
                "list_agents",
                "List all agents in the network",
                list_agents
            )
    
    def _connect_agents(self):
        """Register each agent as a tool for the other agents."""
        for agent_id, agent in self.agents.items():
            # For each agent, create tools to call other agents
            for target_id, target_agent in self.agents.items():
                if agent_id == target_id:
                    continue  # Skip self-registration
                
                # Create a function to call the target agent
                def call_agent(message: str, target_id=target_id):
                    """Call another agent with a message and get their response."""
                    # In a real implementation, this would call the agent's LLM
                    target_agent_name = self.agents[target_id].name
                    
                    # For simulation purposes, we'll return a simple acknowledgment
                    return json.dumps({
                        "status": "success",
                        "message": f"Message sent to {target_agent_name}",
                        "request_id": str(uuid.uuid4())
                    })
                
                # Register the tool
                agent.register_custom_tool(
                    f"call_{target_id}",
                    f"Send a message to the {target_id} agent and get their response",
                    call_agent
                )
    
    def _share_workspace(self):
        """Share the workspace with all agents."""
        # Initialize the shared workspace with empty sections
        self.shared_workspace = {
            "research": {},
            "analysis": {},
            "planning": {},
            "creative": {},
            "summary": {}
        }
        
        # Update each agent's context with the network ID
        for agent_id, agent in self.agents.items():
            agent.update_context("network_id", self.network_id)
            agent.update_context("agent_id", agent_id)
            agent.update_context("agent_role", agent_id)
    
    def update_workspace(self, section: str, key: str, value: Any, from_agent: str) -> None:
        """Update a section of the workspace and share with all agents."""
        if section not in self.shared_workspace:
            self.shared_workspace[section] = {}
        
        self.shared_workspace[section][key] = value
        
        # Add a message to the history
        self.add_message(
            from_agent, 
            f"Updated workspace: {section}/{key} with new information"
        )
    
    def add_message(self, from_agent: str, message: str) -> None:
        """Add a message to the network communication log."""
        agent_name = self.agents[from_agent].name
        self.message_history.append({
            "from": agent_name,
            "agent_id": from_agent,
            "message": message,
            "timestamp": "now"  # In a real implementation, use actual timestamps
        })
    
    def set_topic(self, topic: str) -> None:
        """Set a topic for discussion in the network."""
        # Update the workspace with the new topic
        self.update_workspace("summary", "current_topic", topic, "coordinator")
        
        # Update all agents' context with the topic
        for agent_id, agent in self.agents.items():
            agent.update_context("current_topic", topic)
    
    def interact_with_agent(self, agent_id: str) -> None:
        """Allow the user to interact with a specific agent."""
        if agent_id not in self.agents:
            print(f"Agent '{agent_id}' not found in the network.")
            return
        
        agent = self.agents[agent_id]
        agent_name = agent.name
        
        print(f"\n=== Interacting with {agent_name} Agent ===")
        
        # Create a graph with just this agent
        agent_node = agent.create_agent(self.llm)
        
        # Create a simple graph with just this agent
        graph = create_mcp_langgraph(
            self.llm,
            name=f"{agent_name}Graph",
            system_message=agent.get_context("system_message")
        )
        
        # Start the interaction loop
        print(f"You are now chatting with the {agent_name} Agent. Type 'exit' to end.")
        
        conversation_history = []
        
        while True:
            # Get user input
            user_input = input(f"\nYou to {agent_name}: ")
            
            if user_input.lower() == "exit":
                print(f"Ending conversation with {agent_name}.")
                break
            
            # Add to conversation history
            conversation_history.append(HumanMessage(content=user_input))
            
            # Create a state with the messages
            state = {"messages": conversation_history}
            
            # Run the graph
            result = graph.invoke(state)
            
            # Get the AI response
            messages = result.get("messages", [])
            last_ai_message = next((msg for msg in reversed(messages) if isinstance(msg, AIMessage)), None)
            
            if last_ai_message:
                print(f"{agent_name}: {last_ai_message.content}")
                conversation_history.append(last_ai_message)
            else:
                print(f"{agent_name}: I'm not sure how to respond to that.")
    
    def list_agents(self) -> None:
        """List all agents in the network with their specialties."""
        print("\n=== Agents in the Network ===")
        for agent_id, agent in self.agents.items():
            agent_name = agent.name
            print(f"- {agent_name} ({agent_id})")
    
    def show_workspace(self) -> None:
        """Show the current state of the shared workspace."""
        print("\n=== Shared Workspace ===")
        for section, data in self.shared_workspace.items():
            print(f"\n{section.upper()}:")
            if not data:
                print("  No data yet")
            else:
                for key, value in data.items():
                    if isinstance(value, dict) or isinstance(value, list):
                        print(f"  {key}: {json.dumps(value)[:100]}...")
                    else:
                        print(f"  {key}: {value}")
    
    def show_messages(self) -> None:
        """Show the network message history."""
        print("\n=== Network Messages ===")
        if not self.message_history:
            print("No messages yet")
        else:
            for msg in self.message_history[-10:]:  # Show last 10 messages
                print(f"{msg['from']}: {msg['message']}")


def main():
    """Run the agent network example."""
    print("=== LangGraph Agent Network Example ===")
    print("This example demonstrates a network of specialized agents built with LangGraph.")
    print("The agents can communicate with each other and share context using the MCP protocol.")
    
    # Create the agent network
    network = LangGraphAgentNetwork()
    
    # Main interaction loop
    while True:
        print("\n=== Agent Network Menu ===")
        print("1. List all agents")
        print("2. Chat with an agent")
        print("3. Set discussion topic")
        print("4. Show workspace")
        print("5. Show recent messages")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ")
        
        if choice == "1":
            network.list_agents()
        
        elif choice == "2":
            network.list_agents()
            agent_id = input("\nEnter agent ID to chat with: ")
            if agent_id in network.agents:
                network.interact_with_agent(agent_id)
            else:
                print(f"Agent '{agent_id}' not found.")
        
        elif choice == "3":
            topic = input("Enter a topic for discussion: ")
            network.set_topic(topic)
            print(f"Topic set to: {topic}")
        
        elif choice == "4":
            network.show_workspace()
        
        elif choice == "5":
            network.show_messages()
        
        elif choice == "6":
            print("Exiting agent network example.")
            break
        
        else:
            print("Invalid choice. Please enter a number from 1 to 6.")


if __name__ == "__main__":
    main()