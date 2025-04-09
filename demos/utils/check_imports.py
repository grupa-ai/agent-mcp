"""
Check Imports for MCPAgent Project.

This script checks if all required dependencies for the MCPAgent project are available.
"""

import importlib
import sys

def check_import(module_name, display_name=None):
    """Check if a module can be imported and print the result."""
    if display_name is None:
        display_name = module_name
        
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "unknown version")
        print(f"✓ {display_name} is available (version: {version})")
        return True
    except ImportError as e:
        print(f"✗ {display_name} is NOT available: {e}")
        return False

def main():
    """Check all required imports."""
    print("=== Checking Required Dependencies ===\n")
    
    # Basic Python version check
    python_version = ".".join(map(str, sys.version_info[:3]))
    print(f"Python version: {python_version}")
    
    # Core dependencies
    check_import("autogen", "AutoGen")
    check_import("openai", "OpenAI API")
    
    # LangGraph dependencies
    check_import("langchain_core", "LangChain Core")
    check_import("langchain_openai", "LangChain OpenAI")
    check_import("langgraph", "LangGraph")
    
    # Check our own modules
    try:
        import mcp_agent
        print("✓ MCPAgent module is available")
    except ImportError as e:
        print(f"✗ MCPAgent module is NOT available: {e}")

if __name__ == "__main__":
    main()