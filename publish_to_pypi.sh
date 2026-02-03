#!/bin/bash

# PyPI Publishing Script for agent-mcp
# This script builds and publishes the package to PyPI

set -e  # Exit on error

echo "🚀 Starting PyPI publishing process for agent-mcp..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo -e "${RED}Error: setup.py not found. Please run this script from the project root.${NC}"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(grep -E "version\s*=" setup.py | head -1 | sed -E "s/.*version\s*=\s*['\"]([^'\"]+)['\"].*/\1/")
echo -e "${YELLOW}Current version: ${CURRENT_VERSION}${NC}"

# Check if version was updated
if [ -z "$CURRENT_VERSION" ]; then
    echo -e "${RED}Error: Could not determine version from setup.py${NC}"
    exit 1
fi

# Install/upgrade build tools
echo -e "\n${GREEN}📦 Installing/upgrading build tools...${NC}"
python3 -m pip install --upgrade build twine setuptools wheel

# Clean previous builds
echo -e "\n${GREEN}🧹 Cleaning previous builds...${NC}"
rm -rf build/ dist/ *.egg-info/
rm -f dist/*.whl dist/*.tar.gz

# Build the package
echo -e "\n${GREEN}🔨 Building package...${NC}"
python3 -m build

# Check build output
if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
    echo -e "${RED}Error: Build failed - dist directory is empty${NC}"
    exit 1
fi

echo -e "\n${GREEN}✅ Build successful! Files in dist/:${NC}"
ls -lh dist/

# Ask for confirmation before uploading
echo -e "\n${YELLOW}⚠️  Ready to upload to PyPI${NC}"
echo -e "Version: ${CURRENT_VERSION}"
echo -e "Files to upload:"
ls -1 dist/

read -p "Do you want to upload to PyPI? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}Upload cancelled. You can upload manually later with:${NC}"
    echo -e "  twine upload dist/*"
    exit 0
fi

# Upload to PyPI
echo -e "\n${GREEN}📤 Uploading to PyPI...${NC}"
echo -e "${YELLOW}Note: You'll need to enter your PyPI credentials${NC}"
twine upload dist/*

echo -e "\n${GREEN}✅ Publishing complete!${NC}"
echo -e "Your package should be available at: https://pypi.org/project/agent-mcp/${CURRENT_VERSION}/"
echo -e "\nTest installation with: pip install --upgrade agent-mcp==${CURRENT_VERSION}"
