"""
Command-line interface for the Agent MCP package.
"""
import argparse
import logging
from typing import Optional

def main():
    """Entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description="Agent MCP - Multi-agent Collaboration Platform")
    parser.add_argument(
        "--version", 
        action="store_true", 
        help="Show version information"
    )
    parser.add_argument(
        "-v", 
        "--verbose", 
        action="count", 
        default=0, 
        help="Increase verbosity (use -vv for debug level)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if args.version:
        from agent_mcp import __version__
        print(f"Agent MCP version {__version__}")
        return
    
    # Default action (you can add more commands here)
    print("Agent MCP - Use --help for usage information")

if __name__ == "__main__":
    main()
