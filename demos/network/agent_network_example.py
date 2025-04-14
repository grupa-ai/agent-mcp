"""
Agent Network Example using MCPAgent.

This example demonstrates a network of agents that can communicate with each other
and share context, creating a simple agent social network. The user can interact
with any agent in the network, and agents can call other agents as tools.
"""

import os
import json
from typing import Dict, List, Any, Optional
import time

# Import AutoGen components and MCPAgent
from autogen import UserProxyAgent
from agent_mcp import MCPAgent

# Check for API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

# LLM configuration - using GPT-3.5 for faster responses, but can be switched to GPT-4
config = {
    "config_list": [{"model": "gpt-3.5-turbo", "api_key": api_key}],
}

# Define agent specialties and personalities
AGENT_PROFILES = {
    "coordinator": {
        "name": "Coordinator",
        "system_message": """You are the Coordinator agent who manages the network.
You can connect agents, share information, and help route messages to the right specialist.
You maintain a global view of the agent network and its capabilities.
Always be helpful, concise, and informative.""",
        "specialty": "coordination",
        "connections": ["researcher", "analyst", "creative", "planner"]
    },
    "researcher": {
        "name": "Researcher",
        "system_message": """You are the Researcher agent who specializes in finding information.
You love discovering facts, searching for evidence, and sharing your knowledge.
You're methodical, detail-oriented, and cite sources when possible.
Always be informative, thorough, and accurate.""",
        "specialty": "research",
        "connections": ["coordinator", "analyst"]
    },
    "analyst": {
        "name": "Analyst",
        "system_message": """You are the Analyst agent who excels at interpreting data.
You can evaluate information, identify patterns, and provide insights.
You're logical, critical, and good at understanding implications.
Always be analytical, balanced, and data-driven.""",
        "specialty": "analysis",
        "connections": ["coordinator", "researcher", "planner"]
    },
    "creative": {
        "name": "Creative",
        "system_message": """You are the Creative agent who generates innovative ideas.
You can think outside the box, create content, and suggest novel approaches.
You're imaginative, artistic, and full of unique perspectives.
Always be original, expressive, and inspirational.""",
        "specialty": "creativity",
        "connections": ["coordinator", "planner"]
    },
    "planner": {
        "name": "Planner",
        "system_message": """You are the Planner agent who designs strategies and organizes tasks.
You can create roadmaps, set milestones, and optimize workflows.
You're structured, forward-thinking, and efficient.
Always be practical, organized, and goal-oriented.""",
        "specialty": "planning",
        "connections": ["coordinator", "analyst", "creative"]
    }
}

class AgentNetwork:
    """A network of MCPAgents that can interact with each other and the user."""
    
    def __init__(self):
        self.agents = {}
        self.user = None
        self.current_topic = None
        
    def create_network(self):
        """Create all agents in the network and connect them.
        
        This method initializes all agents defined in AGENT_PROFILES, creates a user proxy agent,
        and establishes connections between agents based on their defined relationships.
        Each agent is registered as a tool for its connected agents.
        """
        # First create all agents
        for agent_id, profile in AGENT_PROFILES.items():
            agent = MCPAgent(
                name=profile["name"],
                system_message=profile["system_message"],
                llm_config=config,
                human_input_mode="NEVER"  # We'll handle human input separately
            )
            
            # Add agent-specific context
            agent.update_context("profile", {
                "specialty": profile["specialty"],
                "connections": profile["connections"]
            })
            
            self.agents[agent_id] = agent
            print(f"Created agent: {profile['name']} ({agent_id})")
        
        # Create user proxy for human interaction
        self.user = UserProxyAgent(
            name="User",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=0
        )
        
        # Now connect agents to each other
        for agent_id, profile in AGENT_PROFILES.items():
            agent = self.agents[agent_id]
            
            # Register each connected agent as a tool
            for connection_id in profile["connections"]:
                if connection_id in self.agents:
                    connected_agent = self.agents[connection_id]
                    agent.register_agent_as_tool(connected_agent)
                    print(f"Connected {agent.name} to {connected_agent.name}")
        
        print("\nAgent network created successfully!")
        
    def set_topic(self, topic):
        """Set a topic for discussion in the network.
        
        Args:
            topic: The topic to be discussed across the network.
            
        This method updates the context of all agents with the new topic
        and its timestamp for synchronized discussions.
        """
        self.current_topic = topic
        
        # Share the topic with all agents
        for agent_id, agent in self.agents.items():
            agent.update_context("current_topic", {
                "title": topic,
                "timestamp": time.time()
            })
            
        print(f"\nTopic set: {topic}")
    
    def interact_with_agent(self, agent_id):
        """Allow the user to interact with a specific agent.
        
        Args:
            agent_id: The identifier of the agent to interact with.
            
        This method enables direct conversation with a chosen agent,
        supports topic-aware discussions, and allows switching between agents.
        Type 'exit' to end conversation or 'switch:agent_id' to change agents.
        """
        if agent_id not in self.agents:
            print(f"Agent '{agent_id}' not found. Available agents: {', '.join(self.agents.keys())}")
            return
            
        agent = self.agents[agent_id]
        print(f"\n--- Starting interaction with {agent.name} ({agent_id}) ---")
        
        if self.current_topic:
            print(f"Current topic: {self.current_topic}")
        
        # Get initial message from user
        initial_message = input(f"\nYour message to {agent.name}: ")
        
        # Create a conversation chain that includes the agent's context
        messages = [{"role": "user", "content": initial_message}]
        
        # Get agent response
        response = agent.generate_reply(messages=messages, sender=self.user)
        print(f"\n{agent.name}: {response}")
        
        # Continue the conversation until user exits
        while True:
            # Check if user wants to exit
            next_message = input("\nYour response (or type 'exit' to end, 'switch:agent_id' to change agents): ")
            
            if next_message.lower() == 'exit':
                print(f"--- Ending interaction with {agent.name} ---")
                break
                
            if next_message.lower().startswith('switch:'):
                new_agent_id = next_message.split(':', 1)[1].strip()
                print(f"--- Switching from {agent.name} to {new_agent_id} ---")
                self.interact_with_agent(new_agent_id)
                break
            
            # Add to messages and get response
            messages.append({"role": "user", "content": next_message})
            response = agent.generate_reply(messages=messages, sender=self.user)
            print(f"\n{agent.name}: {response}")
            
            # Add agent response to message history
            messages.append({"role": "assistant", "content": response})
    
    def share_knowledge(self, from_agent_id, to_agent_id, knowledge_key, knowledge_value):
        """Share specific knowledge from one agent to another.
        
        Args:
            from_agent_id: The source agent's identifier
            to_agent_id: The target agent's identifier
            knowledge_key: The key under which to store the knowledge
            knowledge_value: The knowledge content to share
            
        This method enables direct knowledge transfer between agents
        by updating the target agent's context with specified information.
        """
        if from_agent_id not in self.agents or to_agent_id not in self.agents:
            print("One or both agent IDs are invalid.")
            return
            
        # Get the agents
        from_agent = self.agents[from_agent_id]
        to_agent = self.agents[to_agent_id]
        
        # Share the knowledge
        to_agent.update_context(knowledge_key, knowledge_value)
        
        print(f"Shared knowledge '{knowledge_key}' from {from_agent.name} to {to_agent.name}")
    
    def broadcast_message(self, from_agent_id, message):
        """Broadcast a message from one agent to all connected agents.
        
        Args:
            from_agent_id: The broadcasting agent's identifier
            message: The message content to broadcast
            
        This method sends a message to all agents connected to the source agent,
        storing it in their contexts with timestamp information.
        """
        if from_agent_id not in self.agents:
            print(f"Agent '{from_agent_id}' not found.")
            return
            
        from_agent = self.agents[from_agent_id]
        profile = AGENT_PROFILES[from_agent_id]
        
        # Send to all connected agents
        for connection_id in profile["connections"]:
            if connection_id in self.agents:
                to_agent = self.agents[connection_id]
                
                # Create a message in the agent's context
                message_key = f"message_from_{from_agent_id}_{int(time.time())}"
                message_value = {
                    "from": from_agent.name,
                    "content": message,
                    "timestamp": time.time()
                }
                
                to_agent.update_context(message_key, message_value)
                print(f"Broadcast message from {from_agent.name} to {to_agent.name}")
    
    def list_agents(self):
        """List all agents in the network with their specialties.
        
        This method prints a directory of all agents in the network,
        showing their names, IDs, and specialties for easy reference.
        """
        print("\n--- Agent Network Directory ---")
        for agent_id, agent in self.agents.items():
            profile = agent.get_context("profile")
            specialty = profile.get("specialty") if profile else "unknown"
            print(f"- {agent.name} ({agent_id}): {specialty}")
    
    def get_context(self, agent_id, key):
        """Get a context value from an agent.
        
        Args:
            agent_id: The identifier of the agent
            key: The context key to retrieve
            
        Returns:
            The context value if found, None otherwise
        """
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return agent.get_context(key)
    
    def interact_with_agent_programmatically(self, agent_id, message):
        """
        Interact with an agent programmatically without requiring user input.
        
        This method is similar to interact_with_agent but allows for automation
        in scripts and demonstrations.
        
        Args:
            agent_id: The ID of the agent to interact with
            message: The message to send to the agent
            
        Returns:
            The agent's response as a string
        """
        if agent_id not in self.agents:
            print(f"Agent '{agent_id}' not found in the network.")
            return "Error: Agent not found"
            
        agent = self.agents[agent_id]
        
        # Include current topic in the context if available
        if self.current_topic:
            # Check if agent has the current_topic in context
            if not agent.has_context("current_topic"):
                agent.update_context("current_topic", self.current_topic)
        
        # Format the user message
        print(f"\nMessage to {agent.name}: {message}")
        
        # Send message to the agent
        response = agent.generate_reply(
            messages=[{"role": "user", "content": message}]
        )
        
        print(f"\n{agent.name}: {response}")
        return response

def main():
    """Run the agent network example."""
    print("=== Agent Network Example ===")
    print("Creating a network of specialized agents that can communicate with each other.")
    
    # Create the agent network
    network = AgentNetwork()
    network.create_network()
    
    # Main interaction loop
    while True:
        print("\n=== Agent Network Menu ===")
        print("1. List all agents")
        print("2. Set a discussion topic")
        print("3. Talk to an agent")
        print("4. Share knowledge between agents")
        print("5. Broadcast a message")
        print("6. Exit")
        
        choice = input("\nSelect an option (1-6): ")
        
        if choice == "1":
            network.list_agents()
            
        elif choice == "2":
            topic = input("Enter a topic for discussion: ")
            network.set_topic(topic)
            
        elif choice == "3":
            network.list_agents()
            agent_id = input("\nEnter the agent ID you want to talk to: ")
            network.interact_with_agent(agent_id)
            
        elif choice == "4":
            network.list_agents()
            from_agent = input("\nEnter the source agent ID: ")
            to_agent = input("Enter the target agent ID: ")
            key = input("Enter the knowledge key: ")
            value = input("Enter the knowledge value: ")
            network.share_knowledge(from_agent, to_agent, key, value)
            
        elif choice == "5":
            network.list_agents()
            from_agent = input("\nEnter the broadcasting agent ID: ")
            message = input("Enter the message to broadcast: ")
            network.broadcast_message(from_agent, message)
            
        elif choice == "6":
            print("Exiting the Agent Network Example. Goodbye!")
            break
            
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()