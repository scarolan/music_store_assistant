#!/bin/bash

# 🎸 Pre-Flight Check Script
# Validates demo readiness (does not start anything)
# Use start_demo.sh to launch the demo environment
# Run this from the repository root directory

set -e

# Change to repository root (parent of demo directory)
cd "$(dirname "$0")/.."

echo "🎸 Music Store Assistant - Pre-Flight Check"
echo "Validates your demo setup (does not start anything)"
echo "==========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_item() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1"
        return 1
    fi
}

warn_item() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Check if server is running
echo "1. Checking server status..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    check_item "Server is running on http://localhost:8000"
    SERVER_RUNNING=1
else
    echo -e "${RED}✗${NC} Server is NOT running"
    echo "   Start with: demo/start_demo.sh"
    SERVER_RUNNING=0
fi
echo ""

# 2. Check environment variables in .env file
echo "2. Checking OTEL configuration..."
if [ -f ".env" ]; then
    check_item ".env file exists"

    if grep -q "^OTEL_EXPORTER_OTLP_ENDPOINT=" .env; then
        check_item "OTEL_EXPORTER_OTLP_ENDPOINT is set in .env"
    else
        warn_item "OTEL_EXPORTER_OTLP_ENDPOINT not set in .env (traces won't export)"
    fi

    if grep -q "^OTEL_EXPORTER_OTLP_HEADERS=" .env; then
        check_item "OTEL_EXPORTER_OTLP_HEADERS is set in .env"
    else
        warn_item "OTEL_EXPORTER_OTLP_HEADERS not set in .env (auth will fail)"
    fi
else
    echo -e "${RED}✗${NC} .env file not found"
    echo "   Copy .env.example to .env and configure your OTEL credentials"
fi
echo ""

# 3. Check database
echo "3. Checking database..."
if [ -f "Chinook.db" ]; then
    check_item "Chinook.db exists"
else
    echo -e "${RED}✗${NC} Chinook.db not found"
    echo "   Download with: curl -o Chinook.db https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
fi
echo ""

# 4. Test API call if server is running
if [ "$SERVER_RUNNING" -eq 1 ]; then
    echo "4. Testing API call..."
    RESPONSE=$(curl -s -X POST http://localhost:8000/chat \
        -H "Content-Type: application/json" \
        -d '{"message":"What albums does Pink Floyd have?","thread_id":"demo-test-123","customer_id":1}' \
        2>&1)

    if echo "$RESPONSE" | grep -q "response" 2>/dev/null; then
        check_item "API responds to queries"
    else
        warn_item "API call succeeded but response format unexpected"
    fi
    echo ""
fi

# 5. Check if slides exist
echo "5. Checking presentation files..."
if [ -f "demo/slides.md" ]; then
    check_item "demo/slides.md exists"
else
    warn_item "demo/slides.md not found"
fi

if [ -f "demo/LIGHTNING_TALK.md" ]; then
    check_item "demo/LIGHTNING_TALK.md exists"
else
    warn_item "demo/LIGHTNING_TALK.md not found"
fi

if [ -f "demo/SPEAKER_NOTES.md" ]; then
    check_item "demo/SPEAKER_NOTES.md exists"
else
    warn_item "demo/SPEAKER_NOTES.md not found"
fi
echo ""

# 6. Check for screenshot directory
echo "6. Checking backup screenshots..."
if [ -d "/tmp/screenshots" ]; then
    SCREENSHOT_COUNT=$(ls -1 /tmp/screenshots/*.png 2>/dev/null | wc -l)
    if [ "$SCREENSHOT_COUNT" -gt 0 ]; then
        check_item "Found $SCREENSHOT_COUNT screenshot(s) in /tmp/screenshots/"
    else
        warn_item "/tmp/screenshots/ exists but empty - capture backup screenshots!"
    fi
else
    warn_item "/tmp/screenshots/ not found - creating it now"
    mkdir -p /tmp/screenshots
    echo "   📸 Capture these screenshots before your talk:"
    echo "      1. happy-path-trace.png (clean trace)"
    echo "      2. long-conversation-tokens.png (token growth)"
    echo "      3. failed-trace-error.png (error example)"
    echo "      4. dashboard-overview.png (metrics view)"
fi
echo ""

# 7. Check log file for errors
if [ "$SERVER_RUNNING" -eq 1 ]; then
    echo "7. Checking server logs..."
    if [ -f "/tmp/music-store.log" ]; then
        ERROR_COUNT=$(grep -i "error" /tmp/music-store.log | grep -v "Failed to export span batch code: 401" | wc -l | tr -d ' ')
        AUTH_ERRORS=$(grep -c "authentication error" /tmp/music-store.log 2>/dev/null || echo 0)
        AUTH_ERRORS=$(echo "$AUTH_ERRORS" | tr -d ' \n')

        if [ "$AUTH_ERRORS" -gt 0 ]; then
            echo -e "${RED}✗${NC} Found $AUTH_ERRORS OTEL authentication error(s)"
            echo "   Check your OTEL credentials in .env"
        elif [ "$ERROR_COUNT" -gt 0 ]; then
            warn_item "Found $ERROR_COUNT error(s) in logs (excluding OTEL auth)"
        else
            echo -e "${GREEN}✓${NC} No critical errors in logs"
        fi
    else
        warn_item "Server log not found at /tmp/music-store.log"
    fi
    echo ""
fi

# 8. Summary
echo "==========================================="
echo "📊 Demo Readiness Summary"
echo "==========================================="
echo ""

if [ "$SERVER_RUNNING" -eq 1 ]; then
    echo -e "${GREEN}✓${NC} Server is ready"
    echo "   Customer UI: http://localhost:8000"
    echo "   Admin UI: http://localhost:8000/admin"
else
    echo -e "${RED}✗${NC} Server needs to be started"
fi
echo ""

echo "📝 Next Steps:"
echo "   1. Open Grafana Cloud and test this query:"
echo "      {service.name=\"music-store-assistant\"}"
echo ""
echo "   2. Identify your 3 demo traces:"
echo "      - Happy path (clean music query)"
echo "      - Long conversation (token growth)"
echo "      - Failed trace (0 response chars)"
echo ""
echo "   3. Take backup screenshots (save to /tmp/screenshots/)"
echo ""
echo "   4. Review speaker notes:"
echo "      cat demo/SPEAKER_NOTES.md"
echo ""
echo "   5. Practice the demo at least 3 times!"
echo ""

# Final readiness check
if [ "$SERVER_RUNNING" -eq 1 ] && [ -f "demo/slides.md" ] && [ -f "demo/SPEAKER_NOTES.md" ]; then
    echo -e "${GREEN}🎸 You're ready to rock! Good luck with the talk! 🎤${NC}"
else
    echo -e "${YELLOW}⚠ Some items need attention before the demo${NC}"
fi

echo ""
