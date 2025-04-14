"""
Collaborative Task Example using MCPAgent.

This example demonstrates a team of agents working together on a shared task,
with a user interacting with them throughout the process. Agents will collaborate
by sharing research, analysis, and planning information.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional

# Import AutoGen components and MCPAgent
from autogen import UserProxyAgent
from agent_mcp.mcp_agent import MCPAgent

# Check for API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

# LLM configuration
config = {
    "config_list": [{"model": "gpt-3.5-turbo", "api_key": api_key}],
    "temperature": 0.7,
}

class CollaborativeProject:
    """A collaborative project where agents work together on a task."""
    
    def __init__(self, project_name="Research Project"):
        """Initialize a new collaborative project."""
        self.project_name = project_name
        self.agents = {}
        self.user = None
        self.project_context = {
            "title": project_name,
            "status": "initialized",
            "created_at": time.time(),
            "tasks": {},
            "research": {},
            "analysis": {},
            "plan": {},
            "messages": []
        }
        
        # Initialize the shared workspace
        self.workspace = {
            "project": self.project_context,
            "last_updated": time.time()
        }
    
    def create_team(self):
        """Create a team of specialized agents for the project."""
        # Create project manager
        self.agents["manager"] = MCPAgent(
            name="ProjectManager",  # Removed whitespace from the name
            system_message="""You are the Project Manager agent.
You coordinate the work of the research team, assign tasks, track progress,
and ensure everyone is working effectively. You have a clear view of the big picture
and help keep the project on track. When interacting with the user, be concise,
professional, and always focus on making project-related decisions.
            
When communicating with other agents, reference relevant context from the shared workspace,
and continually update the project plan as information evolves.""",
            llm_config=config
        )
        
        # Create researcher
        self.agents["researcher"] = MCPAgent(
            name="Researcher",
            system_message="""You are the Researcher agent.
Your role is to gather information, find facts, and provide well-researched content
for the project. Be thorough, detail-oriented, and always cite your sources when possible.
Focus on collecting accurate, relevant information on topics assigned by the Project Manager.
            
When you discover new information, add it to the shared workspace so other team members
can use it in their work. Ask specific questions to clarify research requirements.""",
            llm_config=config
        )
        
        # Create analyst
        self.agents["analyst"] = MCPAgent(
            name="Analyst",
            system_message="""You are the Analyst agent.
Your job is to evaluate the research, identify patterns, derive insights, and make
recommendations based on data. Be logical, critical, and balanced in your analysis.
Use quantitative and qualitative approaches as appropriate.
            
Review findings from the Researcher, provide meaningful interpretations, and update
the shared workspace with your analysis. Focus on what the information means for the project goals.""",
            llm_config=config
        )
        
        # Create content specialist
        self.agents["content"] = MCPAgent(
            name="ContentSpecialist",  # Removed whitespace from the name
            system_message="""You are the Content Specialist agent.
You excel at crafting clear, compelling content based on research and analysis.
Your role is to take the project's information and create well-structured deliverables
that effectively communicate the key points.
            
Review research and analysis from other team members, organize information in a logical way,
and create drafts in the shared workspace. Focus on clarity, accuracy, and engagement.""",
            llm_config=config
        )
        
        # Create user proxy for human interaction
        self.user = UserProxyAgent(
            name="User",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=0
        )
        
        # Connect agents to each other as tools
        self._connect_agents()
        
        # Share the workspace with all agents
        self._share_workspace()
        
        print(f"Team created for project: {self.project_name}")
        
    def _connect_agents(self):
        """Register each agent as a tool for the other agents."""
        agent_ids = list(self.agents.keys())
        
        for agent_id in agent_ids:
            for other_id in agent_ids:
                if agent_id != other_id:
                    self.agents[agent_id].register_agent_as_tool(self.agents[other_id])
        
        print("Agents connected for collaboration")
    
    def _share_workspace(self):
        """Share the workspace with all agents."""
        for agent_id, agent in self.agents.items():
            agent.update_context("workspace", self.workspace)
            
            # Add agent specific info
            agent.update_context("role", {
                "id": agent_id,
                "name": agent.name,
                "primary_responsibility": agent_id
            })
        
        print("Shared workspace initialized")
    
    def update_workspace(self, section, key, value):
        """Update a section of the workspace and share with all agents."""
        if section in self.project_context:
            if isinstance(self.project_context[section], dict):
                self.project_context[section][key] = value
            else:
                print(f"Section {section} is not a dictionary and cannot be updated with a key.")
                return
        else:
            print(f"Section {section} not found in project context.")
            return
        
        # Update timestamp
        self.workspace["last_updated"] = time.time()
        
        # Share updated workspace with all agents
        for agent in self.agents.values():
            agent.update_context("workspace", self.workspace)
            
        print(f"Workspace updated: Added {key} to {section}")
    
    def add_message(self, from_agent, message):
        """Add a message to the project communication log."""
        msg = {
            "from": from_agent,
            "timestamp": time.time(),
            "content": message
        }
        
        self.project_context["messages"].append(msg)
        self.workspace["last_updated"] = time.time()
        
        # Share updated workspace with all agents
        for agent in self.agents.values():
            agent.update_context("workspace", self.workspace)
            
        print(f"Message added from {from_agent}")
    
    def set_project_topic(self, topic, description):
        """Set the project topic and description."""
        self.project_context["title"] = topic
        self.project_context["description"] = description
        self.project_context["status"] = "topic_set"
        self.workspace["last_updated"] = time.time()
        
        # Share with all agents
        for agent in self.agents.values():
            agent.update_context("workspace", self.workspace)
            
        print(f"Project topic set: {topic}")
    
    def assign_task(self, agent_id, task_name, description):
        """Assign a task to a specific agent."""
        if agent_id not in self.agents:
            print(f"Agent {agent_id} not found.")
            return
            
        task_id = f"task_{int(time.time())}"
        
        task = {
            "id": task_id,
            "name": task_name,
            "description": description,
            "assigned_to": agent_id,
            "status": "assigned",
            "created_at": time.time()
        }
        
        # Add to tasks
        self.project_context["tasks"][task_id] = task
        self.workspace["last_updated"] = time.time()
        
        # Share with all agents
        for agent in self.agents.values():
            agent.update_context("workspace", self.workspace)
            
        # Notify the assigned agent specifically
        self.agents[agent_id].update_context("new_task", task)
        
        print(f"Task '{task_name}' assigned to {self.agents[agent_id].name}")
        return task_id
    
    def update_task_status(self, task_id, status, result=None):
        """Update the status of a task."""
        if task_id not in self.project_context["tasks"]:
            print(f"Task {task_id} not found.")
            return
            
        self.project_context["tasks"][task_id]["status"] = status
        self.project_context["tasks"][task_id]["updated_at"] = time.time()
        
        if result:
            self.project_context["tasks"][task_id]["result"] = result
            
        self.workspace["last_updated"] = time.time()
        
        # Share with all agents
        for agent in self.agents.values():
            agent.update_context("workspace", self.workspace)
            
        print(f"Task {task_id} status updated to {status}")
    
    def interact_with_agent(self, agent_id):
        """Allow the user to interact with a specific agent."""
        if agent_id not in self.agents:
            print(f"Agent '{agent_id}' not found. Available agents: {', '.join(self.agents.keys())}")
            return
            
        agent = self.agents[agent_id]
        print(f"\n--- Starting interaction with {agent.name} ({agent_id}) ---")
        
        # Get initial message from user
        initial_message = input(f"\nYour message to {agent.name}: ")
        
        # Create a conversation chain that includes the agent's context
        messages = [{"role": "user", "content": initial_message}]
        
        # Get agent response
        response = agent.generate_reply(messages=messages, sender=self.user)
        print(f"\n{agent.name}: {response}")
        
        # Add to project messages
        self.add_message(agent.name, response)
        
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
            
            # Add message from user to project
            self.add_message("User", next_message)
            
            # Add to messages and get response
            messages.append({"role": "user", "content": next_message})
            response = agent.generate_reply(messages=messages, sender=self.user)
            print(f"\n{agent.name}: {response}")
            
            # Add agent response to project and message history
            self.add_message(agent.name, response)
            messages.append({"role": "assistant", "content": response})
    
    def list_agents(self):
        """List all agents in the team."""
        print("\n--- Project Team Directory ---")
        for agent_id, agent in self.agents.items():
            role = agent.get_context("role")
            print(f"- {agent.name} ({agent_id})")
    
    def show_workspace(self):
        """Display the current state of the workspace."""
        print("\n--- Project Workspace ---")
        print(f"Project: {self.project_context['title']}")
        print(f"Status: {self.project_context['status']}")
        
        if "description" in self.project_context:
            print(f"Description: {self.project_context['description']}")
        
        print("\nTasks:")
        if self.project_context["tasks"]:
            for task_id, task in self.project_context["tasks"].items():
                print(f"- [{task['status']}] {task['name']} (Assigned to: {task['assigned_to']})")
        else:
            print("No tasks yet")
        
        print("\nResearch Items:")
        if self.project_context["research"]:
            for key, value in self.project_context["research"].items():
                if isinstance(value, dict) and "title" in value:
                    print(f"- {value['title']}")
                else:
                    print(f"- {key}")
        else:
            print("No research items yet")
        
        print("\nAnalysis Items:")
        if self.project_context["analysis"]:
            for key, value in self.project_context["analysis"].items():
                if isinstance(value, dict) and "title" in value:
                    print(f"- {value['title']}")
                else:
                    print(f"- {key}")
        else:
            print("No analysis items yet")
        
        print("\nRecent Messages:")
        messages = self.project_context["messages"][-5:] if self.project_context["messages"] else []
        if messages:
            for msg in messages:
                print(f"- {msg['from']}: {msg['content'][:50]}..." if len(msg['content']) > 50 else f"- {msg['from']}: {msg['content']}")
        else:
            print("No messages yet")

def main():
    """Run the collaborative project example."""
    print("=== Collaborative Project Example ===")
    print("This example demonstrates agents working together on a shared project.")
    
    # Create a new project
    project_name = input("Enter a name for your project: ")
    project = CollaborativeProject(project_name)
    project.create_team()
    
    # Main interaction loop
    while True:
        print("\n=== Project Menu ===")
        print("1. List team members")
        print("2. Set project topic and description")
        print("3. Show workspace")
        print("4. Assign a task")
        print("5. Talk to a team member")
        print("6. Add research item")
        print("7. Add analysis")
        print("8. Exit")
        
        choice = input("\nSelect an option (1-8): ")
        
        if choice == "1":
            project.list_agents()
            
        elif choice == "2":
            topic = input("Enter the project topic: ")
            description = input("Enter a brief description: ")
            project.set_project_topic(topic, description)
            
        elif choice == "3":
            project.show_workspace()
            
        elif choice == "4":
            project.list_agents()
            agent_id = input("\nAssign to which team member? ")
            if agent_id in project.agents:
                task_name = input("Task name: ")
                description = input("Task description: ")
                project.assign_task(agent_id, task_name, description)
            else:
                print(f"Agent '{agent_id}' not found.")
            
        elif choice == "5":
            project.list_agents()
            agent_id = input("\nWhich team member do you want to talk to? ")
            project.interact_with_agent(agent_id)
            
        elif choice == "6":
            title = input("Research item title: ")
            content = input("Research content: ")
            source = input("Source (optional): ")
            
            research_item = {
                "title": title,
                "content": content,
                "source": source,
                "added_at": time.time()
            }
            
            key = title.lower().replace(" ", "_")
            project.update_workspace("research", key, research_item)
            
        elif choice == "7":
            title = input("Analysis title: ")
            content = input("Analysis content: ")
            
            analysis_item = {
                "title": title,
                "content": content,
                "added_at": time.time()
            }
            
            key = title.lower().replace(" ", "_")
            project.update_workspace("analysis", key, analysis_item)
            
        elif choice == "8":
            print("Exiting the Collaborative Project Example. Goodbye!")
            break
            
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()