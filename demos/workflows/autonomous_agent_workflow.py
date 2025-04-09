"""
Autonomous Agent Collaboration Example

This script demonstrates how agents can autonomously collaborate without
hardcoded interaction patterns. The flow is determined by the agents themselves
based on their analysis of the conversation.
"""

import os
import sys
import time
from typing import Dict, Any, Optional

# Import the required langgraph components
try:
    from langgraph.graph import StateGraph
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_openai import ChatOpenAI
except ImportError:
    print("Error: Required packages not found. Make sure langgraph, langchain-core, and langchain-openai are installed.")
    sys.exit(1)

class Agent:
    """A simple agent implementation that can make decisions about collaboration."""
    
    def __init__(self, name: str, specialty: str, system_message: str = None):
        """Initialize the agent with a name, specialty, and optional system message."""
        self.name = name
        self.specialty = specialty
        self.system_message = system_message or f"You are {name}, an expert in {specialty}."
        
        # Create the OpenAI chat model
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.2,
            api_key=api_key,
            model_kwargs={"messages": [{"role": "system", "content": self.system_message}]}
        )
    
    def respond(self, messages: list) -> Dict[str, Any]:
        """Generate a response and determine who to collaborate with next."""
        
        # Convert to format expected by langchain
        lc_messages = []
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"], name=msg.get("name")))
        
        # Generate a response to the conversation
        response = self.llm.invoke(lc_messages)
        content = response.content
        
        # Determine who should respond next
        # We'll use a special format in the response: [NEXT: agent_name] to indicate
        collaboration_prompt = f"""
        Based on your response, determine which team member should contribute next:
        - Researcher (information gathering)
        - Analyst (data interpretation)
        - Creative (innovative ideas)
        - Planner (implementation strategy)
        - Coordinator (synthesizing and directing)
        
        Choose the most appropriate agent based on what's needed next.
        Format your choice as [NEXT: agent_name]
        """
        
        next_agent_decision = self.llm.invoke([
            HumanMessage(content=collaboration_prompt + "\n\nYour response was: " + content)
        ])
        
        # Extract the next agent from the decision
        next_agent = "coordinator"  # Default
        decision_text = next_agent_decision.content.lower()
        
        if "[next:" in decision_text:
            # Extract the agent name from the format [NEXT: agent_name]
            start = decision_text.find("[next:") + 6
            end = decision_text.find("]", start)
            if end > start:
                next_agent = decision_text[start:end].strip().lower()
        
        # Return both the response and the next agent decision
        return {
            "response": content,
            "next": next_agent
        }

class AutonomousCollaboration:
    """Manages autonomous collaboration between agents."""
    
    def __init__(self):
        """Initialize the collaboration environment."""
        self.agents = {}
        self.message_history = []
    
    def create_agents(self):
        """Create the agent team.
        
        This method initializes a team of specialized agents with predefined roles
        and system messages. Each agent is created with specific expertise and
        personality traits to contribute effectively to the collaboration.
        """
        self.agents = {
            "coordinator": Agent(
                name="Coordinator",
                specialty="coordinating team efforts",
                system_message="""You are the Coordinator. Your role is to guide the research process,
                ensure all perspectives are considered, and synthesize information from all team members.
                When appropriate, suggest which agent would be best to handle the next step."""
            ),
            "researcher": Agent(
                name="Researcher",
                specialty="information gathering and fact-finding",
                system_message="""You are the Researcher. Your role is to gather relevant information,
                identify key facts, and provide evidence-based context for the topic.
                When appropriate, suggest which agent would be best to handle the next step."""
            ),
            "analyst": Agent(
                name="Analyst",
                specialty="analyzing data and identifying patterns",
                system_message="""You are the Analyst. Your role is to interpret information,
                identify patterns, evaluate implications, and provide critical insights.
                When appropriate, suggest which agent would be best to handle the next step."""
            ),
            "creative": Agent(
                name="Creative",
                specialty="generating innovative ideas and approaches",
                system_message="""You are the Creative. Your role is to think outside the box,
                generate innovative ideas, make unexpected connections, and envision new possibilities.
                When appropriate, suggest which agent would be best to handle the next step."""
            ),
            "planner": Agent(
                name="Planner",
                specialty="creating implementation strategies",
                system_message="""You are the Planner. Your role is to develop practical strategies,
                create roadmaps, identify necessary resources, and outline implementation steps.
                When appropriate, suggest which agent would be best to handle the next step."""
            )
        }
        
        print(f"Created {len(self.agents)} agents:")
        for agent_id, agent in self.agents.items():
            print(f"- {agent.name} ({agent_id}): {agent.specialty}")
    
    def run_collaboration(self, topic: str, max_steps: int = 5):
        """Run an autonomous collaboration on the given topic.
        
        Args:
            topic: The subject matter for agents to collaborate on
            max_steps: Maximum number of interaction steps (default: 5)
            
        This method orchestrates the autonomous collaboration process where agents
        interact and build upon each other's contributions. Each agent decides
        which team member should contribute next based on the conversation flow.
        The process continues until max_steps is reached.
        """
        print(f"\n{'='*80}")
        print(f"AUTONOMOUS COLLABORATION ON: {topic}")
        print(f"{'='*80}\n")
        
        print("Starting collaboration process...\n")
        
        # Add the initial message from the user
        self.message_history.append({
            "role": "user",
            "content": f"I need your help researching this topic: {topic}. Please collaborate as a team to explore it thoroughly."
        })
        
        # Start with the coordinator
        current_agent = "coordinator"
        
        # Track the interaction flow
        interaction_flow = []
        
        # Run for max_steps or until we detect a loop
        for step in range(1, max_steps + 1):
            agent = self.agents[current_agent]
            print(f"\n[Step {step}] {agent.name} is responding...")
            
            # Get the agent's response
            result = agent.respond(self.message_history)
            
            # Record the response in the message history
            self.message_history.append({
                "role": "assistant",
                "name": agent.name,
                "content": result["response"]
            })
            
            # Display a summary of the response
            response_summary = result["response"]
            if len(response_summary) > 150:
                response_summary = response_summary[:150] + "..."
            print(f"Response: {response_summary}")
            
            # Track the flow
            interaction_flow.append({
                "step": step,
                "agent": agent.name,
                "next": result["next"]
            })
            
            # Update the current agent based on the agent's decision
            print(f"{agent.name} suggests that {result['next']} should respond next.")
            current_agent = result["next"]
            
            # Add a short delay to make the output more readable
            time.sleep(1)
        
        print(f"\n{'='*80}")
        print(f"AUTONOMOUS COLLABORATION COMPLETE")
        print(f"{'='*80}\n")
        
        # Display the interaction flow
        print("Agent Interaction Flow:")
        print("-" * 40)
        for step in interaction_flow:
            print(f"Step {step['step']}: {step['agent']} → {step['next']}")
        
        return self.message_history

def main():
    """Run the autonomous collaboration example.
    
    This function serves as the entry point for the script, setting up and
    executing an autonomous collaboration session. It accepts an optional
    command-line argument for the collaboration topic, defaulting to
    'Sustainable urban development' if none is provided.
    """
    # Get topic from command line argument or use default
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "Sustainable urban development"
    
    # Create and run the collaboration
    collab = AutonomousCollaboration()
    collab.create_agents()
    collab.run_collaboration(topic, max_steps=5)

if __name__ == "__main__":
    main()