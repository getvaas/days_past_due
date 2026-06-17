#!/bin/bash

# Clean test cache and volumes for Days Past Due (DPD)
# Use this if you encounter issues with cached dependencies.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================="
echo "  Clean Test Cache & Volumes"
echo "================================================="
echo ""

echo -e "${YELLOW}This will remove:${NC}"
echo "  - pip cache volume (days-past-due-test-cache)"
echo "  - Python caches (__pycache__, .pytest_cache)"
echo ""
echo -e "${YELLOW}Next test run will re-download dependencies${NC}"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "Cleaning..."

# Get absolute path to project root (script lives in ./scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Remove pip cache volume
if docker volume inspect days-past-due-test-cache &> /dev/null; then
    docker volume rm days-past-due-test-cache
    echo -e "${GREEN}✓ Removed pip cache volume${NC}"
else
    echo "- pip cache volume not found (already clean)"
fi

# Remove Python caches (__pycache__ and .pytest_cache)
if find "${PROJECT_ROOT}" -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -not -path '*/.venv/*' | grep -q .; then
    find "${PROJECT_ROOT}" -type d \( -name '__pycache__' -o -name '.pytest_cache' \) -not -path '*/.venv/*' -exec rm -rf {} + 2>/dev/null || true
    echo -e "${GREEN}✓ Removed Python caches (__pycache__, .pytest_cache)${NC}"
else
    echo "- No Python caches found"
fi

echo ""
echo -e "${GREEN}✓ Cleanup complete!${NC}"
echo ""
echo "Run './scripts/run-tests.sh' to rebuild cache"
echo ""
