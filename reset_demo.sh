#!/bin/bash
# ============================================================
#  BMW Capstone P11 — Reset Local Demo State
#
#  Safely clears local demonstration state:
#    1. Stops running local background processes (Spark, API, Frontend)
#    2. Resets Kafka broker container and wipes topics/messages
#    3. Clears local streaming checkpoints
#    4. Clears local run logs and PID files
#
#  NOTE: This script DOES NOT touch Terraform infrastructure,
#  AWS resources, or any project source code. It only resets
#  local demo runtime state.
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  BMW Capstone P11 — Local Demo Reset         ${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════${NC}"
echo ""

# 1. Stop background processes if running
echo -e "${CYAN}[1/4]${NC} Stopping local processes..."
if [ -f "$PROJECT_DIR/.spark.pid" ]; then
  SPARK_PID=$(cat "$PROJECT_DIR/.spark.pid" 2>/dev/null || true)
  [ -n "$SPARK_PID" ] && kill -9 "$SPARK_PID" 2>/dev/null || true
  rm -f "$PROJECT_DIR/.spark.pid"
fi
if [ -f "$PROJECT_DIR/.api.pid" ]; then
  API_PID=$(cat "$PROJECT_DIR/.api.pid" 2>/dev/null || true)
  [ -n "$API_PID" ] && kill -9 "$API_PID" 2>/dev/null || true
  rm -f "$PROJECT_DIR/.api.pid"
fi
if [ -f "$PROJECT_DIR/.frontend.pid" ]; then
  FE_PID=$(cat "$PROJECT_DIR/.frontend.pid" 2>/dev/null || true)
  [ -n "$FE_PID" ] && kill -9 "$FE_PID" 2>/dev/null || true
  rm -f "$PROJECT_DIR/.frontend.pid"
fi

# Stop any orphan processes on ports 8000 and 5173
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
echo -e "${GREEN}[✓]${NC} Local background processes stopped."

# 2. Reset Kafka in Docker
echo -e "${CYAN}[2/4]${NC} Resetting local Kafka broker..."
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  docker compose down -v --remove-orphans 2>/dev/null || true
  echo -e "${GREEN}[✓]${NC} Kafka container stopped and topic data reset."
else
  echo -e "${YELLOW}[!]${NC} Docker not active — skipped Kafka container teardown."
fi

# 3. Clear local checkpoints
echo -e "${CYAN}[3/4]${NC} Clearing PySpark streaming checkpoints..."
rm -rf "$PROJECT_DIR/checkpoints" "$PROJECT_DIR/spark-checkpoints"
rm -rf "$PROJECT_DIR"/*.checkpoint
echo -e "${GREEN}[✓]${NC} Streaming checkpoints removed."

# 4. Clear local execution logs
echo -e "${CYAN}[4/4]${NC} Clearing local logs and PID markers..."
rm -f "$PROJECT_DIR/.spark.log" "$PROJECT_DIR/.api.log" "$PROJECT_DIR/.frontend.log"
rm -f "$PROJECT_DIR"/*.log "$PROJECT_DIR"/.*.log "$PROJECT_DIR"/*.pid "$PROJECT_DIR"/.*.pid
echo -e "${GREEN}[✓]${NC} Local logs and markers cleared."

echo ""
echo -e "${BOLD}${GREEN}Demo reset complete!${NC}"
echo -e "To start a fresh demonstration run:"
echo -e "  ${BOLD}bash start.sh${NC}"
echo ""
