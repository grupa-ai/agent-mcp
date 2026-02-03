#!/usr/bin/env python3
"""
PyPI Publishing Script for agent-mcp
This script automates the process of building and publishing to PyPI
"""

import os
import sys
import subprocess
import re
import shutil
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(message, color=Colors.NC):
    """Print colored message"""
    print(f"{color}{message}{Colors.NC}")

def get_version_from_file(filepath, pattern):
    """Extract version from a file using regex pattern"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            match = re.search(pattern, content)
            if match:
                return match.group(1)
    except Exception as e:
        print_colored(f"Error reading {filepath}: {e}", Colors.RED)
    return None

def update_version(new_version):
    """Update version in all necessary files"""
    files_to_update = [
        ('setup.py', r"version\s*=\s*['\"]([^'\"]+)['\"]", f'version="{new_version}"'),
        ('pyproject.toml', r'version\s*=\s*"([^"]+)"', f'version = "{new_version}"'),
        ('agent_mcp/__init__.py', r"__version__\s*=\s*['\"]([^'\"]+)['\"]", f'__version__ = "{new_version}"'),
    ]
    
    updated = []
    for filepath, pattern, replacement in files_to_update:
        if not os.path.exists(filepath):
            print_colored(f"Warning: {filepath} not found", Colors.YELLOW)
            continue
            
        with open(filepath, 'r') as f:
            content = f.read()
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(filepath, 'w') as f:
                f.write(new_content)
            updated.append(filepath)
            print_colored(f"✓ Updated {filepath}", Colors.GREEN)
        else:
            print_colored(f"⚠ Could not update {filepath} (pattern not found)", Colors.YELLOW)
    
    return updated

def run_command(cmd, check=True):
    """Run a shell command"""
    print_colored(f"Running: {cmd}", Colors.BLUE)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print_colored(f"Error: {result.stderr}", Colors.RED)
        sys.exit(1)
    return result

def main():
    print_colored("🚀 PyPI Publishing Script for agent-mcp", Colors.GREEN)
    print_colored("=" * 50, Colors.BLUE)
    
    # Check if we're in the right directory
    if not os.path.exists("setup.py"):
        print_colored("Error: setup.py not found. Please run from project root.", Colors.RED)
        sys.exit(1)
    
    # Get current version
    current_version = get_version_from_file("setup.py", r"version\s*=\s*['\"]([^'\"]+)['\"]")
    if not current_version:
        print_colored("Error: Could not determine current version", Colors.RED)
        sys.exit(1)
    
    print_colored(f"\nCurrent version: {current_version}", Colors.YELLOW)
    
    # Ask if user wants to update version
    response = input("\nDo you want to update the version? (yes/no): ").strip().lower()
    if response in ['yes', 'y']:
        new_version = input(f"Enter new version (current: {current_version}): ").strip()
        if new_version and new_version != current_version:
            update_version(new_version)
            current_version = new_version
            print_colored(f"\n✓ Version updated to {current_version}", Colors.GREEN)
    
    # Install/upgrade build tools
    print_colored("\n📦 Installing/upgrading build tools...", Colors.GREEN)
    run_command("python3 -m pip install --upgrade build twine setuptools wheel --quiet")
    
    # Clean previous builds
    print_colored("\n🧹 Cleaning previous builds...", Colors.GREEN)
    for dir_path in ['build', 'dist', '*.egg-info']:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print_colored(f"  Removed {dir_path}", Colors.YELLOW)
    
    # Build the package
    print_colored("\n🔨 Building package...", Colors.GREEN)
    run_command("python3 -m build")
    
    # Check build output
    dist_dir = Path("dist")
    if not dist_dir.exists() or not list(dist_dir.glob("*")):
        print_colored("Error: Build failed - dist directory is empty", Colors.RED)
        sys.exit(1)
    
    print_colored("\n✅ Build successful! Files created:", Colors.GREEN)
    for file in dist_dir.glob("*"):
        size = file.stat().st_size / 1024  # Size in KB
        print_colored(f"  - {file.name} ({size:.1f} KB)", Colors.YELLOW)
    
    # Ask for confirmation before uploading
    print_colored(f"\n⚠️  Ready to upload to PyPI", Colors.YELLOW)
    print_colored(f"Version: {current_version}", Colors.BLUE)
    
    response = input("\nDo you want to upload to PyPI? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print_colored("\nUpload cancelled. You can upload manually later with:", Colors.YELLOW)
        print_colored("  twine upload dist/*", Colors.BLUE)
        sys.exit(0)
    
    # Upload to PyPI
    print_colored("\n📤 Uploading to PyPI...", Colors.GREEN)
    print_colored("Note: You'll need to enter your PyPI credentials", Colors.YELLOW)
    run_command("twine upload dist/*")
    
    print_colored("\n✅ Publishing complete!", Colors.GREEN)
    print_colored(f"Package available at: https://pypi.org/project/agent-mcp/{current_version}/", Colors.BLUE)
    print_colored(f"\nTest installation with: pip install --upgrade agent-mcp=={current_version}", Colors.YELLOW)

if __name__ == "__main__":
    main()
