#!/bin/bash
# ============================================================
#  BMW Capstone P11 — One-Click Startup
#  Double-click this file (or run: bash start.sh) to launch:
#    1. Kafka       (Docker)
#    2. FastAPI     (Python venv)
#    3. React UI    (Vite dev server)
#  The browser will open automatically when everything is up.
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$PROJECT_DIR/.venv"
BROWSER_OPENED=false

# ── Colours ──────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[BMW]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

echo ""
echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║    BMW Connected Mobility — Capstone P11     ║${NC}"
echo -e "${BOLD}${BLUE}║         One-Click Startup Script             ║${NC}"
echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_DIR"

# ── Java Environment Setup ───────────────────────────────────
if [ -z "$JAVA_HOME" ]; then
  if command -v /usr/libexec/java_home &>/dev/null; then
    JH=$(/usr/libexec/java_home 2>/dev/null || true)
    [ -n "$JH" ] && export JAVA_HOME="$JH" && export PATH="$JAVA_HOME/bin:$PATH"
  fi
  if [ -z "$JAVA_HOME" ]; then
    if [ -d "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home" ]; then
      export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
      export PATH="$JAVA_HOME/bin:$PATH"
    elif [ -d "/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home" ]; then
      export JAVA_HOME="/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
      export PATH="$JAVA_HOME/bin:$PATH"
    elif [ -d "/usr/lib/jvm/default-java" ]; then
      export JAVA_HOME="/usr/lib/jvm/default-java"
      export PATH="$JAVA_HOME/bin:$PATH"
    elif [ -d "/usr/lib/jvm/java-17-openjdk-amd64" ]; then
      export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
      export PATH="$JAVA_HOME/bin:$PATH"
    fi
  fi
fi

# ── Step 1: Docker / Kafka ────────────────────────────────────
log "Starting Kafka (Docker)…"
if ! command -v docker &>/dev/null; then
  warn "Docker not found — skipping Kafka. Install Docker Desktop to enable Kafka."
else
  if docker info &>/dev/null 2>&1; then
    docker compose up -d 2>&1 | grep -E "(Starting|Running|Created|done)" || true
    ok "Kafka is running on port 9092"
  else
    warn "Docker daemon not running — skipping Kafka. Start Docker Desktop and re-run."
  fi
fi

# ── Step 2: FastAPI (background) ─────────────────────────────
log "Starting FastAPI server on port 8000…"
if [ -d "$VENV_DIR" ]; then
  PYTHON="$VENV_DIR/bin/python"
  UVICORN="$VENV_DIR/bin/uvicorn"
else
  PYTHON="python3"
  UVICORN="uvicorn"
fi

# Kill any existing FastAPI on 8000
lsof -ti :8000 | xargs kill -9 2>/dev/null || true

nohup "$UVICORN" api.main:app --reload --port 8000 \
  > "$PROJECT_DIR/.api.log" 2>&1 &
API_PID=$!
echo $API_PID > "$PROJECT_DIR/.api.pid"

# Wait for FastAPI to be ready
for i in $(seq 1 15); do
  sleep 1
  if curl -s http://localhost:8000/api/health &>/dev/null; then
    ok "FastAPI is live at http://localhost:8000"
    break
  fi
  if [ $i -eq 15 ]; then
    warn "FastAPI taking longer than expected. Check .api.log for errors."
  fi
  echo -ne "  Waiting for API… ($i/15)\r"
done
echo ""

# ── Step 3: Vite dev server (background) ─────────────────────
log "Starting React frontend (Vite) on port 5173…"

# Kill any existing Vite on 5173
lsof -ti :5173 | xargs kill -9 2>/dev/null || true

cd "$FRONTEND_DIR"

# Install node_modules if needed
if [ ! -d "node_modules" ]; then
  log "Installing npm dependencies…"
  npm install --silent
fi

nohup npm run dev -- --port 5173 \
  > "$PROJECT_DIR/.frontend.log" 2>&1 &
VITE_PID=$!
echo $VITE_PID > "$PROJECT_DIR/.frontend.pid"
cd "$PROJECT_DIR"

# Wait for Vite to be ready
for i in $(seq 1 20); do
  sleep 1
  if curl -s http://localhost:5173 &>/dev/null; then
    ok "Frontend is live at http://localhost:5173"
    break
  fi
  echo -ne "  Waiting for Vite… ($i/20)\r"
done
echo ""

# ── Step 4: Open browser ──────────────────────────────────────
sleep 1
log "Opening dashboard in browser…"
open "http://localhost:5173" 2>/dev/null || \
  xdg-open "http://localhost:5173" 2>/dev/null || \
  warn "Could not auto-open browser — visit http://localhost:5173"

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          All Services Are Running! ✓         ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  🌐  Dashboard  →  ${BOLD}http://localhost:5173${NC}"
echo -e "  🔌  FastAPI    →  ${BOLD}http://localhost:8000${NC}"
echo -e "  📨  Kafka      →  ${BOLD}localhost:9092${NC}"
echo ""
echo -e "  📄  API logs   →  .api.log"
echo -e "  📄  UI logs    →  .frontend.log"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${NC} to stop everything"
echo ""

# ── Trap: clean up on Ctrl+C ──────────────────────────────────
cleanup() {
  echo ""
  log "Shutting down all services…"

  [ -f "$PROJECT_DIR/.spark.pid" ] && kill "$(cat "$PROJECT_DIR/.spark.pid")" 2>/dev/null; rm -f "$PROJECT_DIR/.spark.pid"
  [ -f "$PROJECT_DIR/.api.pid" ] && kill "$(cat "$PROJECT_DIR/.api.pid")" 2>/dev/null; rm -f "$PROJECT_DIR/.api.pid"
  [ -f "$PROJECT_DIR/.frontend.pid" ] && kill "$(cat "$PROJECT_DIR/.frontend.pid")" 2>/dev/null; rm -f "$PROJECT_DIR/.frontend.pid"

  if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    cd "$PROJECT_DIR"
    docker compose down 2>/dev/null || true
  fi

  ok "All services stopped. Goodbye!"
  exit 0
}
trap cleanup INT TERM

# Keep script alive
wait
