#!/bin/bash
# PocketAgent - Start both backend and frontend locally
# Usage: bash start.sh

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_LOG="$ROOT_DIR/tmp/backend.log"
FRONTEND_LOG="$ROOT_DIR/tmp/frontend.log"
BACKEND_PID=""
FRONTEND_PID=""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

mkdir -p "$ROOT_DIR/tmp"

# Prefer project venv uvicorn (README uses .venv; some setups use venv).
# Checks both Unix (bin/) and Windows (Scripts/) venv layouts.
resolve_uvicorn() {
    for candidate in \
        "$ROOT_DIR/backend/.venv/bin/uvicorn" \
        "$ROOT_DIR/backend/.venv/Scripts/uvicorn.exe" \
        "$ROOT_DIR/backend/venv/bin/uvicorn" \
        "$ROOT_DIR/backend/venv/Scripts/uvicorn.exe"; do
        if [ -n "$candidate" ] && { [ -x "$candidate" ] || [ -f "$candidate" ]; }; then
            echo "$candidate"
            return
        fi
    done
    echo "uvicorn"
}

UVICORN_BIN="$(resolve_uvicorn)"

wait_for_health() {
    curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1
}

port_in_use() {
    ss -tln 2>/dev/null | grep -q ':8000 ' || netstat -tln 2>/dev/null | grep -q ':8000 '
}

show_backend_failure() {
    echo ""
    echo -e "${RED}Backend failed to start.${NC}"
    if [ -f "$BACKEND_LOG" ]; then
        echo -e "${YELLOW}Last lines of $BACKEND_LOG:${NC}"
        tail -20 "$BACKEND_LOG"
    fi
    echo ""
    echo "Common fixes:"
    echo "  1. cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    echo "  2. If port 8000 is busy, stop the other terminal running start.sh, or kill the process holding it:"
    echo "       Linux/macOS : fuser -k 8000/tcp"
    echo "       Windows PS  : Get-NetTCPConnection -LocalPort 8000 | Stop-Process -Id { $_.OwningProcess }"
    echo "       Git-Bash    : netstat -ano | grep ':8000'   (then: taskkill /F /PID <pid>)"
    exit 1
}

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && echo "  Backend stopped"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && echo "  Frontend stopped"
    echo -e "${GREEN}Done.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ---------- Backend ----------
echo -e "${YELLOW}Starting backend (FastAPI)...${NC}"
cd "$ROOT_DIR/backend"

if wait_for_health; then
    echo -e "  ${GREEN}Backend already running at http://localhost:8000${NC}"
else
    if port_in_use; then
        echo -e "  ${RED}Port 8000 is in use but /health is not responding.${NC}"
        echo "  Stop the stale process, then run start.sh again:"
        echo "    Linux/macOS : fuser -k 8000/tcp"
        echo "    Windows PS  : Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force"
        echo "    Git-Bash    : netstat -ano | grep ':8000'   (then: taskkill /F /PID <pid>)"
        show_backend_failure
    fi

    if [ "$UVICORN_BIN" = "uvicorn" ]; then
        echo -e "  ${YELLOW}Warning: backend virtualenv not found — using system uvicorn.${NC}"
        echo -e "  ${YELLOW}Run: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
    else
        echo "  Using: $UVICORN_BIN"
    fi

    "$UVICORN_BIN" main:app --reload --port 8000 --host 0.0.0.0 > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!
    echo "  PID: $BACKEND_PID"

    # Wait for backend to be healthy
    echo -n "  Waiting for backend"
    BACKEND_READY=false
    for i in $(seq 1 30); do
        if wait_for_health; then
            BACKEND_READY=true
            echo ""
            echo -e "  ${GREEN}Backend ready at http://localhost:8000${NC}"
            break
        fi
        if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
            echo ""
            show_backend_failure
        fi
        echo -n "."
        sleep 1
    done

    if [ "$BACKEND_READY" = false ]; then
        echo ""
        show_backend_failure
    fi
fi

# ---------- Frontend ----------
echo -e "${YELLOW}Starting frontend (Next.js)...${NC}"
cd "$ROOT_DIR/frontend"
# Ensure frontend .env exists
if [ ! -f .env ]; then
    echo "  Creating frontend/.env from root .env..."
    API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:8000}"
    API_URL="${API_URL%/}"
    WC_ID="$(grep '^NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=' "$ROOT_DIR/.env" 2>/dev/null | cut -d= -f2)"
    if [ -z "$WC_ID" ]; then
        WC_ID="b986e72a6fa82c645da36c67550760ee"
        echo -e "  ${YELLOW}Warning: NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID not found in root .env, using default${NC}"
    fi
    cat > .env << EOF
NEXT_PUBLIC_API_URL=$API_URL
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=$WC_ID
EOF
fi

npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo "  PID: $FRONTEND_PID"

# Wait for frontend to be ready
echo -n "  Waiting for frontend"
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w '' http://127.0.0.1:3000 2>/dev/null; then
        echo ""
        echo -e "  ${GREEN}Frontend ready at http://localhost:3000${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Backend:  http://localhost:8000${NC}"
echo -e "${GREEN}  Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}  API Docs: http://localhost:8000/docs${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Keep running until Ctrl+C
wait
