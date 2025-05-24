"""
HeterogeneousGroupChat - A group chat implementation for heterogeneous agents.

This module provides a high-level abstraction for creating group chats with agents
from different frameworks (Autogen, Langchain, etc.) that can collaborate on tasks.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Union, Sequence
from .mcp_transport import HTTPTransport
from .enhanced_mcp_agent import EnhancedMCPAgent
from .mcp_agent import MCPAgent
import re
import string
import logging
from typing import Dict, Any, Optional, List
import os
import time

logger = logging.getLogger(__name__)

class CoordinatorAgent(EnhancedMCPAgent):
    def __init__(self, group_chat, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.group_chat = group_chat  # Reference to HeterogeneousGroupChat instance

    async def handle_incoming_message(self, message: Dict):

        # First, call the super method to handle default processing
        await super().handle_incoming_message(message)

        # Delegate to the group chat's custom handler
        await self.group_chat._handle_coordinator_message(message, message.get('message_id'))

class ContextAgent(EnhancedMCPAgent):
    """Agent that maintains and provides access to task context and results."""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(
            name=name,
            transport=None,  # No transport needed for internal use
            server_mode=False,
            client_mode=False,
            **kwargs
        )
        self.task_results = {}  # Store task results
        self.task_descriptions = {}  # Store task descriptions
        self._pending_tasks = {}  # Track pending tasks with their completion events
        print(f"[DEBUG] __init__: self ID: {id(self)}, _pending_tasks ID: {id(self._pending_tasks)}")

        logger.info(f"[{self.name}] Initialized as context agent")

    async def query_context(self, query: str) -> Dict[str, Any]:
        """
        Query the context agent for information.
        
        Args:
            query: Natural language query about tasks, results, or context.
                  Can also be a request to generate email content.
            
        Returns:
            Dict with 'answer' and 'supporting_data' keys
        """ 
        # Regular context query
        return await self.generate_response(query)
        
    async def generate_response(self, query: str) -> Dict[str, Any]:
        """Answer general questions about tasks and results."""
        context = {
            "task_descriptions": self.task_descriptions,
            "task_results": {
                tid: str(r)[:500] for tid, r in self.task_results.items()
            }
        }
        
        messages = [{
            "role": "system",
            "content": f"""You are a context assistant that generates responses, results or content based on task as query. 
            You will be given a query, task description and expected to generate a content, response, as result or output
            
            Available context, tasks and their results: {context}
            
            """
        }, {
            "role": "user",
            "content": f"""Generate a response, result or content based on these instructions:
            {query}
            
            """
        }]
        
        try:
            response = await self.a_generate_reply(messages)

             # Ensure we have a valid response
            if not response:
                raise ValueError("Empty response from LLM")
                
            # Handle both string and dictionary responses
            if isinstance(response, str):
                content = response
            elif isinstance(response, dict):
                content = response.get("content", "")
                if not content and "message" in response:
                    content = response.get("message", {}).get("content", "")
            else:
                content = str(response)
                
            print(f"Generated response: {content}")  # Log first 200 chars
            return {
                "answer": content,
                "supporting_data": context
            }
        except Exception as e:
            logger.error(f"Error querying context: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "supporting_data": {}
            }
            

    async def update_task(self, task_id: str, task_data: Dict, result: Optional[Any] = None):
        """Update task information and results."""
        self.task_descriptions[task_id] = task_data.get("description", "No description")
        if result is not None:
            self.task_results[task_id] = result
        logger.debug(f"Updated context for task {task_id}")
 

class HeterogeneousGroupChat:
    """
    A group chat for heterogeneous agents that abstracts away the complexity
    of setting up connections and coordinating tasks between different frameworks.
    """
    
    def __init__(
        self,
        name: str,
        server_url: str = "https://mcp-server-ixlfhxquwq-ew.a.run.app",
        coordinator_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a heterogeneous group chat.
        
        Args:
            name: Name of the group chat
            server_url: URL of the deployed MCP server
            coordinator_config: Optional configuration for the coordinator agent
        """
        self.name = name
        self.server_url = server_url
        self.agents: List[MCPAgent] = []
        self.coordinator: Optional[EnhancedMCPAgent] = None
        self.coordinator_config = coordinator_config or {}
        self.coordinator_url = server_url
        self.agent_tokens: Dict[str, str] = {} # Store agent tokens
        self._register_event = asyncio.Event()
        self._agent_tasks = [] # Initialize list to store agent tasks
        # Initialize directly on the group chat instance first
        self.task_results: Dict[str, Any] = {} 
        self.task_dependencies: Dict[str, Dict] = {}
        self.dependency_results: Dict[str, Any] = {}  # Initialize dependency results
        
        # Store coordinator config for later use
        self.coordinator_config = coordinator_config or {}
        
        # Initialize context agent with default LLM config
        default_llm_config = {
            "config_list": [{
                "model": "gpt-3.5-turbo",
                "api_key": os.getenv("OPENAI_API_KEY"),  # Will be set when coordinator is created
                "api_type": "openai"
            }]
        }
        
        # Use provided config or default
        llm_config = self.coordinator_config.get("llm_config", default_llm_config).copy()
        
        # Ensure config_list exists and has at least one config
        if not llm_config.get("config_list"):
            llm_config["config_list"] = default_llm_config["config_list"]
        
        # Create context agent
        self.context_agent = ContextAgent(
            name=f"{self.name}_context",
            llm_config=llm_config
        )

    def _get_agent_url(self, agent_name: str) -> str:
        """Get the URL for an agent on the deployed server"""
        return f"{self.server_url}/agents/{agent_name}"
        
    def create_coordinator(self, api_key: str) -> CoordinatorAgent:
        """Create the coordinator agent for the group chat"""
        # Avoid creating coordinator if it already exists
        if self.coordinator:
            return self.coordinator
            
        # Define coordinator name (use config if provided, else default)
        coordinator_name = self.coordinator_config.get("name", f"{self.name}Coordinator")
        
        # Create transport for coordinator, passing its name
        coordinator_transport = HTTPTransport.from_url(
            self.server_url, 
            agent_name=coordinator_name
        )
        
        # --- Default Coordinator Configuration ---
        default_config = {
            "name": coordinator_name, 
            "transport": coordinator_transport,
            "system_message": "You are a helpful AI assistant coordinating tasks between other specialized agents. You receive task results and ensure the overall goal is achieved.",
            "llm_config": {
                 # Default model, can be overridden by coordinator_config
                "config_list": [{
                    "model": "gpt-3.5-turbo", 
                    "api_key": api_key
                }],
                "cache_seed": 42 # Or None for no caching
            },
        }
        
        
        # --- Merge Default and User Config --- 
        # User config takes precedence
        final_config = default_config.copy() # Start with defaults
        final_config.update(self.coordinator_config) # Update with user overrides
        
        # Ensure llm_config is properly structured if overridden
        if "llm_config" in self.coordinator_config and "config_list" not in final_config["llm_config"]:
             print("Warning: coordinator_config provided llm_config without config_list. Re-structuring.")
             # Assume the user provided a simple dict like {"api_key": ..., "model": ...}
             # We need to wrap it in config_list for AutoGen
             user_llm_config = final_config["llm_config"]
             final_config["llm_config"] = {
                 "config_list": [user_llm_config],
                 "cache_seed": user_llm_config.get("cache_seed", 42)
             }
        elif "llm_config" in final_config and "api_key" not in final_config["llm_config"].get("config_list", [{}])[0]:
             # If llm_config exists but api_key is missing in the primary config
             print("Warning: api_key missing in llm_config config_list. Injecting from create_coordinator argument.")
             if "config_list" not in final_config["llm_config"]:
                 final_config["llm_config"]["config_list"] = [{}]
             final_config["llm_config"]["config_list"][0]["api_key"] = api_key


        # Update context agent's LLM config to match coordinator's
        if hasattr(self, 'context_agent') and self.context_agent:
            # Get the final config that will be used by the coordinator
            context_llm_config = final_config.get('llm_config', {})
            # Update the context agent's config
            if hasattr(self.context_agent, 'llm_config'):
                self.context_agent.llm_config = context_llm_config
                logger.info(f"Updated context agent's LLM config to match coordinator")
        
        # --- Create Coordinator Agent --- 
        print(f"Creating coordinator with config: {final_config}") # Debug: Log final config
        self.coordinator = CoordinatorAgent(self, **final_config)
        
        # --- Set Message Handler ---
        #self.coordinator.transport.set_message_handler(self._handle_coordinator_message)
        # Use a lambda to explicitly capture the correct 'self' (the HeterogeneousGroupChat instance)
        #self.coordinator.transport.set_message_handler(lambda msg, msg_id: self._handle_coordinator_message(msg, msg_id))

        return self.coordinator
        
    def add_agents(self, agents: Union[MCPAgent, Sequence[MCPAgent]]) -> List[MCPAgent]:
        """
        Add one or more agents to the group chat.
        
        Args:
            agents: A single MCPAgent or a sequence of MCPAgents
            
        Returns:
            List of added agents
            
        Example:
            # Add a single agent
            group.add_agents(agent1)
            
            # Add multiple agents
            group.add_agents([agent1, agent2, agent3])
            
            # Add agents as separate arguments
            group.add_agents(agent1, agent2, agent3)
        """
        if not isinstance(agents, (list, tuple)):
            agents = [agents]
            
        added_agents = []
        for agent in agents:
            # Retrieve token if agent was already registered
            token = self.agent_tokens.get(agent.name)
            if not self.server_url:
                 raise ValueError("Cannot add agents before connecting. Call connect() first.")
                 
            # Create transport for the agent, passing its name and token
            agent.transport = HTTPTransport.from_url(self.server_url, agent_name=agent.name, token=token)
                
            # Set client mode if needed
            if hasattr(agent, 'client_mode'):
                agent.client_mode = True
                
            self.agents.append(agent)
            added_agents.append(agent)
            
        return added_agents
        
    # Alias for backward compatibility
    add_agent = add_agents
        
    async def connect(self):
        """Register all agents and start their processing loops."""
        print("Registering coordinator...")
        coord_task = await self._register_and_start_agent(self.coordinator)
        if not coord_task:
             print("Coordinator registration failed. Aborting connect.")
             return

        print("Registering agents...")
        tasks = [coord_task] # Start with coordinator task
        for agent in self.agents:
            agent_task = await self._register_and_start_agent(agent)
            if agent_task: # Only add task if registration was successful
                tasks.append(agent_task)
            else:
                print(f"Skipping agent {agent.name} due to registration failure.")
                # Optionally, handle failed agents (e.g., remove from group?)

        if not tasks:
            print("No agents were successfully registered and started.")
            return
            
        print(f"All {len(tasks)} agents registered and started.")
        # Store tasks but don't wait for them - they'll run in the background
        self._agent_tasks = tasks
        print("Group chat ready for task submission.")

    async def _register_and_start_agent(self, agent: MCPAgent):
        """Register an agent, start its event stream, and its processors."""
        if not agent.transport or not isinstance(agent.transport, HTTPTransport):
             raise ValueError(f"Agent {agent.name} has no valid HTTPTransport defined.")
             
        response = await agent.transport.register_agent(agent)
        
        # Parse response which may be in {'body': '{...}'} format
        if isinstance(response, dict):
            if 'body' in response:
                # Response is wrapped, parse the body string
                try:
                    response = json.loads(response['body'])
                except json.JSONDecodeError:
                    print(f"Error parsing agent registration response body: {response}")
                    
        if response and isinstance(response, dict) and "token" in response:
            token = response["token"]
            self.agent_tokens[agent.name] = token
            agent.transport.token = token
            agent.transport.auth_token = token
            print(f"Agent {agent.name} registered successfully with token.")

            # Start polling *before* starting the agent's run loop
            await agent.transport.start_polling()
            
            # Start agent's main run loop (message processing, etc.)
            # We create the task but don't await it here; the calling function (connect) will gather tasks.
            task = asyncio.create_task(agent.run())
            self._agent_tasks.append(task) # Store the task
            return task # Return the task for potential gathering
        else:
            print(f"Warning: Agent {agent.name} registration failed or did not return a token. Response: {response}")
            # Don't run the agent if registration fails - it won't be able to communicate
            return None # Indicate failure
        
 
    async def query_context(self, query: str) -> Dict[str, Any]:
        """
        Query the context agent for information about tasks and results.
        
        Args:
            query: Natural language query about tasks, results, or context
            
        Returns:
            Dict with 'answer' and 'supporting_data' keys
        """
        return await self.context_agent.query_context(query)

    def _inject_dependency_results(self, step: Dict, dependency_results: Dict) -> Dict:
        """Injects dependency results into a step's content.

        If the step contains string.Template style placeholders (e.g., ${task_id}),
        it substitutes them with the corresponding results.

        If no placeholders are found, it assumes the agent needs the raw results
        and adds them to the step's content under the key 'dependency_data'.
        """
        if not step:
            return step

        # Check if any part of the step contains a placeholder
        logger.info(f"No placeholders detected in step {step.get('task_id', 'N/A')}. Adding raw dependency data.")
        dependency_data = {}
        for dep_task_id in step.get("depends_on", []):
            result_value = dependency_results.get(dep_task_id)
            if result_value is None:
                logger.warning(f"No result found for dependency '{dep_task_id}' when preparing raw data for step '{step.get('task_id', 'N/A')}'")
                extracted_value = None # Or some placeholder? 
            elif isinstance(result_value, dict):
                 # Prioritize 'output', then 'result', then string representation
                if 'output' in result_value: # Check presence first
                    extracted_value = result_value['output']
                elif 'result' in result_value: # Check presence first
                    extracted_value = result_value['result']
                else:
                    logger.warning(f"Raw dependency '{dep_task_id}': Neither 'output' nor 'result' key found in dict result. Using full dict.")
                    extracted_value = result_value # Pass the whole dict
            else:
                extracted_value = result_value # Pass strings, numbers, lists as-is

            dependency_data[dep_task_id] = extracted_value
            
        # Ensure 'content' exists and add the data
        if "content" not in step:
            step["content"] = {}
        if not isinstance(step["content"], dict):
            logger.warning(f"Step {step.get('task_id', 'N/A')} content is not a dict, cannot add dependency_data. Content: {step['content']}")
        else:
            step["content"]["dependency_data"] = dependency_data
            
        return step

    async def submit_task(self, task: Dict[str, Any], inject_at_submit_time: bool = False) -> None:
        """
        Submit a group task. If inject_at_submit_time is True, inject dependency results into each step now.
        If False, inject at the last possible moment (just before sending to agents).
        """
        # Reset state for new task submission
        self.task_results = {}
        self.context_agent.task_results = {}
        self.context_agent.task_descriptions = {}
        self._pending_tasks = {}  # Track pending tasks with their completion events to ensure its always new for each submission
        print(f"[DEBUG] __init__: self ID: {id(self)}, _pending_tasks ID: {id(self._pending_tasks)}")
        steps = task.get("steps", [])
        self.task_dependencies = {step["task_id"]: step for step in steps} # Store task dependencies

        self._inject_at_submit_time = inject_at_submit_time
        if inject_at_submit_time:
            steps = [self._inject_dependency_results(step, self.task_results) for step in steps]
        self._pending_steps = steps  # Store for later use
        await self._submit_steps(steps)

    async def _submit_steps(self, steps):
        for step in steps:
            try:
                # Only inject here if not already injected at submit time
                if not getattr(self, '_inject_at_submit_time', True):
                    step = self._inject_dependency_results(step, self.task_results)
                
                # Create and store event for this task
                task_id = step['task_id']
                future = asyncio.Future()
                self._pending_tasks[task_id] = future
                print(f"[DEBUG] _submit_steps: Added task {task_id}. Current _pending_tasks: {list(self._pending_tasks.keys())} (ID: {id(self._pending_tasks)})")
                print(f"[DEBUG] Added task {task_id} to pending_tasks")
                # Submit the task
                await self._send_step_to_agent(step)
                
                # Wait for task completion with timeout
                try:
                    await asyncio.wait_for(future, timeout=60)
                    print(f"[DEBUG] Task {task_id} completed with result: {future.result()}")
                except asyncio.TimeoutError:
                    logger.error(f"Task {task_id} timed out")
                    raise TimeoutError(f"Task {task_id} timed out")
                finally:
                    # Clean up
                    self._pending_tasks.pop(task_id, None)
                    
            except Exception as e:
                logger.error(f"Error in step {step.get('task_id')}: {e}")
                raise

    async def _generate_content(self, description: str, content: Dict) -> Dict:
        """Generate content using the ContextAgent based on the task description.
        
        Args:
            description: The task description
            content: Existing content to be augmented with generated content
            
        Returns:
            Dict: Content with generated fields merged in
        """
        # Ensure we have a dictionary to work with
        if not isinstance(content, dict):
            content = {}
            
        try:
            # Generate content using the context agent
            generated = await self.context_agent.generate_response(description)
            
            print(f"Generated content: {generated}")
            if generated and isinstance(generated, dict) and "answer" in generated:
                try:
                    # Try to parse as JSON first
                    generated_content = json.loads(generated["answer"])
                    # If it's a dictionary, merge it intelligently
                    if isinstance(generated_content, dict):
                        # Merge with existing content, with generated content taking precedence
                        content = {**content, **generated_content}
                    # If it's not a dictionary, store it as generated_content
                    else:
                        content["content"] = generated_content # this is the generated content that will be sent to the agent
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, store the raw answer
                    content["content"] = generated["answer"] # this is the generated content that will be sent to the agent
        
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            print(f"Error generating content: {e}")
            content["error"] = str(e)
        
        return content

    async def _send_step_to_agent(self, step):
        # 1-line dependency enforcement: skip if any dependency missing or empty
        #if any(not self.dependency_results.get(dep) for dep in step.get("depends_on", [])):
        #    print(f"Skipping {step['task_id']} because dependencies not satisfied: {step.get('depends_on', [])}")
        #    return
        step = self._inject_dependency_results(step, self.task_results)
        
        # Update context agent with task info
        task_id = step.get("task_id", str(id(step)))
        await self.context_agent.update_task(task_id, step)
        
        print("\n=== Submitting task to group ===")

        # Ensure task is in the correct format
        if not isinstance(step, dict):
            raise ValueError("Invalid task format. Expected a dictionary.")

        # Handle content generation if requested
        if step.get("content", {}).get("generate_content", False):
            description = step.get("description", "")
            if description:
                # Make a copy to avoid modifying the original
                content = step.get("content", {}).copy()
                # Remove the flag before generation
                content.pop("generate_content", None)
                # Generate and merge content
                step["content"] = await self._generate_content(description, content)

        # Store task dependencies from the input task definition
        # We need a dictionary where keys are the step task_ids
        self.task_dependencies[step["task_id"]] = step
        print(f"Parsed Step Dependencies: {self.task_dependencies}")

        # Also store in coordinator instance if it exists
        if self.coordinator:
            # Ensure the coordinator has the dict initialized
            if not hasattr(self.coordinator, 'task_dependencies') or not isinstance(getattr(self.coordinator, 'task_dependencies', None), dict):
                self.coordinator.task_dependencies = {}
            self.coordinator.task_dependencies.update(self.task_dependencies)

        if not self.coordinator or not self.coordinator.transport:
             print("CRITICAL ERROR: Coordinator is not initialized or has no transport. Cannot submit task.")
             return
        
        coordinator_transport = self.coordinator.transport

        print(f"[DEBUG - {self.name}] Starting submit_task loop over {len(self.task_dependencies)} dependencies.", flush=True)
        print(f"***** [{self.name}] Dependencies Content: {self.task_dependencies} *****", flush=True) # Log content before loop

        # Assign tasks to agents based on the structure
        # Submit tasks to their respective agents
        agent_name = step["agent"]
        # Create message with all necessary fields including content
        message = {
            "type": "task",
            "task_id": step["task_id"],
            "description": step["description"],
            "sender": self.coordinator.name,
            "content": step.get("content", {}),  # Include task content
            "depends_on": step.get("depends_on", []),  # Include dependencies
            "reply_to": f"{self.server_url}/message/{self.coordinator.name}" # Full URL for reply
        }
        print(f"Sending task to {agent_name}")
        print(f"Task message: {message}")
        # Use coordinator's transport to send task to agent
        await coordinator_transport.send_message(agent_name, message)
            
        print("Task submitted. Waiting for completion...")
        
    async def wait_for_completion(self, check_interval: float = 1.0):
        """
        Wait for all tasks to complete.
        
        Args:
            check_interval: How often to check for completion in seconds
        """
        if not self.coordinator:
            raise ValueError("Group chat not connected. Call connect() first.")
            
        try:
            while True:
                # Check if all tasks have results
                all_completed = True
                # Use the dependencies stored in the coordinator
                for task_id in self.task_dependencies:
                    # Check both group chat and coordinator results
                    if task_id not in self.task_results and task_id not in self.coordinator.task_results:
                        all_completed = False
                        print(f"Waiting for task {task_id}...")
                        break
                        
                if all_completed:
                    print("\n=== All tasks completed! ===")
                    print("\nResults:")
                    # Merge results from both sources
                    all_results = {**self.task_results, **self.coordinator.task_results}
                    for task_id, result in all_results.items():
                        print(f"\n{task_id}:")
                        print(result)
                    break
                    
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\nStopping group chat...")
            
    async def _handle_coordinator_message(self, message: Dict, message_id: str):
        """Handles messages received by the coordinator's transport."""
        
        if not self.coordinator: # Ensure coordinator exists
            print(f"[Coordinator Handler] Error: Coordinator not initialized. Self ID: {id(self)}")
            return
            
        print(f"\n[Coordinator {self.coordinator.name}] Received message: {message}. Self ID: {id(self)}")        
        
        # Handle messages wrapped in 'body' field
        if isinstance(message, dict) and 'body' in message:
            try:
                if isinstance(message['body'], str):
                    message = json.loads(message['body'])
                else:
                    message = message['body']
                print(f"[Coordinator {self.coordinator.name}] Unwrapped message body: {message}")
            except json.JSONDecodeError:
                print(f"[Coordinator {self.coordinator.name}] Error decoding message body: {message}")
                return
        
        # Look for type and task_id at top level
        msg_type = message.get("type")
        task_id = message.get("task_id")
        
        print(f"[Coordinator {self.coordinator.name}] Processing message type '{msg_type}' for task {task_id}. Current _pending_tasks in handler: {list(self._pending_tasks.keys())} (ID: {id(self._pending_tasks)})")        
        
        if msg_type in ["result", "task_result"]:  # Handle both result types
            # First try direct fields, then try parsing content.text if it exists
            result_content = None
            
            # Try direct fields first
            result_content = message.get("result") or message.get("description")
            
            # If not found, try to parse from content.text
            if result_content is None and "content" in message and isinstance(message["content"], dict):
                content_text = message["content"].get("text")
                if content_text:
                    try:
                        content_data = json.loads(content_text)
                        result_content = content_data.get("result") or content_data.get("description")
                        # Update task_id from content if not set
                        if not task_id and "task_id" in content_data:
                            task_id = content_data["task_id"]
                    except (json.JSONDecodeError, AttributeError, TypeError) as e:
                        print(f"[Coordinator {self.coordinator.name}] Error parsing content.text: {e}")
            
            if task_id and result_content is not None:
                print(f"[Coordinator {self.coordinator.name}] Storing result for task {task_id}")
                # Store result in both the group chat and coordinator
                self.task_results[task_id] = result_content
                self.dependency_results[task_id] = result_content  # Required for template resolution
                if "dependency_results" not in self.coordinator.task_results:
                    self.coordinator.task_results["dependency_results"] = {}
                self.coordinator.task_results["dependency_results"][task_id] = result_content
                self.coordinator.task_results[task_id] = result_content
                print(f"[Coordinator {self.coordinator.name}] Stored result for task {task_id}")
                print(f"[Coordinator {self.coordinator.name}] Stored result: {result_content}...")
                print(f"[Coordinator {self.coordinator.name}] Current task results: {list(self.task_results.keys())}")
                print(f"[Coordinator {self.coordinator.name}] Current dependencies: {self.task_dependencies}")
                
                # Signal task completion if anyone is waiting
                if not hasattr(self, '_pending_tasks'):
                    self._pending_tasks = {}
                print(f"[Coordinator {self.coordinator.name}] Current pending tasks: {list(self._pending_tasks.keys())}")
                print(f"[DEBUG] Checking if task {task_id} is in pending_tasks: {task_id in self._pending_tasks}")
                
                if task_id in self._pending_tasks:
                    print(f"[Coordinator {self.coordinator.name}] Signaling completion for task {task_id}")
                    future = self._pending_tasks[task_id]
                    if not future.done():
                        #future.set_result(result_content)
                        asyncio.get_event_loop().call_soon_threadsafe(lambda: future.set_result(result_content) if not future.done() else None)
                        print(f"[DEBUG] Set result for task {task_id}")
                        await asyncio.sleep(0)
                        print(f"[Coordinator {self.coordinator.name}] Completed task {task_id}")
                        #asyncio.get_running_loop().call_soon(future.set_result, result_content)
                        #asyncio.get_event_loop().call_soon_threadsafe(lambda: future.set_result(result_content) if not future.done() else None)
                    # Clean up the task after signaling
                    #if task_id in self._pending_tasks:
                        #del self._pending_tasks[task_id]
                    print(f"[Coordinator {self.coordinator.name}] Completed task {task_id}")
                else:
                    print(f"[Coordinator {self.coordinator.name}] Task {task_id} not found in pending tasks")
                
                # Acknowledge the message
                try:
                    if message_id:  # Only acknowledge if we have a message ID
                        await self.coordinator.transport.acknowledge_message(self.coordinator.name, message_id)
                        print(f"[Coordinator {self.coordinator.name}] Acknowledged message {message_id}")
                except Exception as e:
                    print(f"[Coordinator {self.coordinator.name}] Error acknowledging message {message_id}: {e}")
                return
            else:
                print(f"[Coordinator {self.coordinator.name}] Received invalid result message (missing task_id or result): {message}")
        elif msg_type == "get_result":  # Handle get result request
            result = None
            if task_id in self.task_results:
                result = self.task_results[task_id]
            elif task_id in self.coordinator.task_results:
                result = self.coordinator.task_results[task_id]
            
            if result:
                print(f"[Coordinator {self.coordinator.name}] Found result for task {task_id}")
                # Send result back
                try:
                    await self.coordinator.transport.send_message(
                        f"{self.server_url}/message/{message.get('sender', 'unknown')}",
                        {
                            "type": "task_result",
                            "task_id": task_id,
                            "result": result
                        }
                    )
                    print(f"[Coordinator {self.coordinator.name}] Sent result for task {task_id}")
                except Exception as e:
                    print(f"[Coordinator {self.coordinator.name}] Error sending result: {e}")
            else:
                print(f"[Coordinator {self.coordinator.name}] No result found for task {task_id}")
        else:
            print(f"[Coordinator {self.coordinator.name}] Received unhandled message type '{msg_type}': {message}")
            # Optionally, acknowledge other messages too or handle errors
            try:
                await self.coordinator.transport.acknowledge_message(message_id)
            except Exception as e:
                print(f"[Coordinator {self.coordinator.name}] Error acknowledging message {message_id}: {e}")

    @property
    def group_state(self) -> dict:
        """
        Returns a merged dictionary of all task results (group and coordinator).
        Agents can use this to access the shared group chat history/results.
        """
        return {**self.task_results, **(self.coordinator.task_results if self.coordinator else {})}

    async def shutdown(self):
        """Gracefully disconnect all agents and cancel their tasks."""
        print(f"Initiating shutdown for {len(self._agent_tasks)} agent tasks...")

        # 1. Cancel all running agent tasks
        for task in self._agent_tasks:
            if task and not task.done():
                print(f"Cancelling task {task.get_name()}...")
                task.cancel()
            
        # Wait for all tasks to be cancelled
        if self._agent_tasks:
            await asyncio.gather(*[t for t in self._agent_tasks if t], return_exceptions=True)
            print("All agent tasks cancelled or finished.")
        self._agent_tasks.clear() # Clear the list of tasks

        # 2. Disconnect transports for all agents (coordinator + regular agents)
        all_agents = [self.coordinator] + self.agents
        disconnect_tasks = []
        for agent in all_agents:
             if hasattr(agent, 'transport') and hasattr(agent.transport, 'disconnect'):
                 print(f"Disconnecting transport for {agent.name}...")
                 disconnect_tasks.append(agent.transport.disconnect())
             
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            print("All agent transports disconnected.")
            
        print("Shutdown complete.")

    # === Minimal free-flow chat: send a message to any agent ===
    async def send_chat_message(self, agent_name, message):
        await self.coordinator.transport.send_message(agent_name, {"type": "message", "content": message})
