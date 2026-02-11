#!/bin/bash

# 🎸 Start Music Store Assistant Demo
# Starts the server and generates initial traffic for dashboard
# Run this from the repository root directory

set -e

# Change to repository root (parent of demo directory)
cd "$(dirname "$0")/.."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🎸 Music Store Assistant - Demo Launcher"
echo "=========================================="
echo ""

# Check if server is already running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC} Server is already running on port 8000"
    read -p "   Kill existing server and restart? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   Stopping existing server..."
        pkill -f "uvicorn src.api:app" || true
        sleep 2
    else
        echo "   Keeping existing server..."
        SKIP_SERVER_START=1
    fi
fi

# Start the server
if [ -z "$SKIP_SERVER_START" ]; then
    echo -e "${BLUE}1. Starting server...${NC}"

    # Check for .env file
    if [ ! -f ".env" ]; then
        echo -e "${RED}✗${NC} .env file not found!"
        echo "   Copy .env.example to .env and configure your API keys"
        exit 1
    fi

    # Check for database
    if [ ! -f "Chinook.db" ]; then
        echo -e "${RED}✗${NC} Chinook.db not found!"
        echo "   Downloading database..."
        curl -L -o Chinook.db https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite
    fi

    # Start server in background
    echo "   Starting uvicorn on http://localhost:8000..."
    PYTHONUNBUFFERED=1 nohup uv run uvicorn src.api:app --host 0.0.0.0 --port 8000 > /tmp/music-store.log 2>&1 &
    SERVER_PID=$!
    echo "   Server PID: $SERVER_PID"

    # Wait for server to be ready (uv can take time to set up environment)
    echo "   Waiting for server to start..."
    echo "   Note: First startup with 'uv run' can take 60-90 seconds while environment is prepared"
    for i in {1..90}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Server is ready! (started in ${i} seconds)"
            break
        fi

        # Show progress dots every 5 seconds
        if [ $((i % 5)) -eq 0 ]; then
            echo "   Still waiting... (${i}s)"
        fi

        sleep 1
        if [ $i -eq 90 ]; then
            echo -e "${RED}✗${NC} Server failed to start within 90 seconds"
            echo "   Process may still be starting. Check if it's running:"
            echo "   ps aux | grep uvicorn"
            echo "   Check logs: tail -f /tmp/music-store.log"
            echo "   Or try running manually: uv run uvicorn src.api:app --host 0.0.0.0 --port 8000"
            exit 1
        fi
    done
    echo ""
fi

# Start continuous traffic generation
echo -e "${BLUE}2. Starting continuous traffic generation...${NC}"
echo "   Traffic will run for 30 minutes (or until you stop the demo)"
echo ""

# Check if traffic generator is already running
if pgrep -f "continuous_traffic.py" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC} Traffic generator already running"
else
    # Start continuous traffic in background
    chmod +x demo/continuous_traffic.py
    nohup uv run python demo/continuous_traffic.py > /tmp/continuous-traffic.log 2>&1 &
    TRAFFIC_PID=$!
    echo "   Traffic generator PID: $TRAFFIC_PID"
    echo "   Logs: /tmp/continuous-traffic.log"

    # Give it a moment to start
    sleep 2

    if pgrep -f "continuous_traffic.py" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Continuous traffic generation started!"
    else
        echo -e "${YELLOW}⚠${NC} Traffic generator may have failed to start (check /tmp/continuous-traffic.log)"
    fi
fi

echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}🎸 Demo is ready!${NC}"
echo "=========================================="
echo ""
echo "📊 Your demo environment:"
echo "   • Server: http://localhost:8000"
echo "   • Customer UI: http://localhost:8000"
echo "   • Admin UI: http://localhost:8000/admin"
echo "   • Server logs: /tmp/music-store.log"
echo ""
echo "📈 Grafana Cloud Query:"
echo "   {service.name=\"music-store-assistant\"}"
echo ""
echo "💡 Next steps:"
echo "   1. Open Grafana Cloud and verify traces are flowing"
echo "   2. Run demo/preflight_check.sh to validate full setup"
echo "   3. Review speaker notes: cat demo/SPEAKER_NOTES.md"
echo ""
echo "🛑 To stop the demo:"
echo "   pkill -f \"uvicorn src.api:app\""
echo "   pkill -f \"continuous_traffic.py\""
echo "   (or use: demo/stop_demo.sh)"
echo ""
echo "📊 Monitor traffic generation:"
echo "   tail -f /tmp/continuous-traffic.log"
echo ""
echo "🔥 To generate additional burst traffic:"
echo "   uv run python demo/generate_traffic.py        # 15 short conversations"
echo "   uv run python demo/generate_long_conversations.py  # 5 long conversations"
echo ""
