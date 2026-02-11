#!/bin/bash

# 🛑 Stop Music Store Assistant Demo
# Stops the server and traffic generation

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🛑 Stopping Music Store Assistant Demo"
echo "========================================"
echo ""

# Stop server
if pgrep -f "uvicorn src.api:app" > /dev/null 2>&1; then
    echo "Stopping server..."
    pkill -f "uvicorn src.api:app"
    sleep 1
    if ! pgrep -f "uvicorn src.api:app" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Server stopped"
    else
        echo -e "${YELLOW}⚠${NC} Server may still be running (trying SIGKILL)"
        pkill -9 -f "uvicorn src.api:app"
    fi
else
    echo -e "${YELLOW}⚠${NC} Server was not running"
fi

# Stop traffic generator
if pgrep -f "continuous_traffic.py" > /dev/null 2>&1; then
    echo "Stopping continuous traffic generator..."
    pkill -f "continuous_traffic.py"
    sleep 1
    if ! pgrep -f "continuous_traffic.py" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Traffic generator stopped"
    else
        echo -e "${YELLOW}⚠${NC} Traffic generator may still be running (trying SIGKILL)"
        pkill -9 -f "continuous_traffic.py"
    fi
else
    echo -e "${YELLOW}⚠${NC} Traffic generator was not running"
fi

echo ""
echo -e "${GREEN}✅ Demo stopped${NC}"
echo ""
echo "📊 View logs:"
echo "   tail /tmp/music-store.log"
echo "   tail /tmp/continuous-traffic.log"
echo ""
