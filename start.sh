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
uvicorn main:app --reload --port 8000 --host 0.0.0.0 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "  PID: $BACKEND_PID"

# Wait for backend to be healthy
echo -n "  Waiting for backend"
for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo ""
        echo -e "  ${GREEN}Backend ready at http://localhost:8000${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# ---------- Frontend ----------
echo -e "${YELLOW}Starting frontend (Next.js)...${NC}"
cd "$ROOT_DIR/frontend"
# Ensure frontend .env exists
if [ ! -f .env ]; then
    echo "  Creating frontend/.env from root .env..."
    API_URL="${NEXT_PUBLIC_API_URL:-http://127.0.0.1:8000}"
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
