#!/bin/bash

# Optimized Test Runner for Days Past Due (DPD)
# Runs the Python test suite inside a Docker container, caching pip downloads
# in a Docker volume so repeated runs are fast. No image rebuilding.

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_IMAGE="python:3.12-slim"
PIP_CACHE_VOLUME="days-past-due-test-cache"
PROJECT_NAME="days-past-due"

# Get absolute path to project root (script lives in ./scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================="
echo "  Days Past Due - Fast Test Runner"
echo "  (Volume-cached pip strategy - super fast!)"
echo "================================================="
echo ""

# Function to print step headers
print_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_step "Step 1: Checking Prerequisites"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

if ! docker ps &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}"

# Create pip cache volume if it doesn't exist
if ! docker volume inspect ${PIP_CACHE_VOLUME} &> /dev/null; then
    echo -e "${YELLOW}Creating pip cache volume (one-time setup)...${NC}"
    docker volume create ${PIP_CACHE_VOLUME}
    echo -e "${GREEN}✓ pip cache volume created${NC}"
else
    echo -e "${GREEN}✓ pip cache volume exists${NC}"
fi

# Run tests in Docker with mounted volumes
print_step "Step 2: Running Tests"
echo "Strategy: Mount source code + cache pip downloads in a volume"
echo "This approach:"
echo "  ✓ Caches pip downloads (fast on 2nd+ runs)"
echo "  ✓ No image rebuilding required"
echo "  ✓ Installs project deps + pytest, then runs the suite"
echo ""
echo -e "${YELLOW}Running test suite...${NC}"
echo ""

START_TIME=$(date +%s)

# Run pytest in container with volumes:
# - Mount source code at /app
# - Mount pip cache volume so downloads persist between runs
# - Install requirements.txt + pytest, then run pytest
set +e  # Temporarily disable exit on error to capture exit code
docker run --rm \
    -v "${PROJECT_ROOT}:/app" \
    -v "${PIP_CACHE_VOLUME}:/root/.cache/pip" \
    -w /app \
    ${PYTHON_IMAGE} \
    bash -c "pip install -q -r requirements.txt pytest && python -m pytest"

TEST_EXIT_CODE=$?
set -e  # Re-enable exit on error

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""

if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ All Tests Passed!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Execution time: ${DURATION} seconds"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ Tests Failed${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Execution time: ${DURATION} seconds"
    echo "Check the output above for test failure details"
    echo ""
    exit 1
fi
