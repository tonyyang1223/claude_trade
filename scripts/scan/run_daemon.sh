#!/bin/bash
# Scan Top 800 cryptocurrencies every 10 minutes
# Usage: nohup bash scripts/scan/run_daemon.sh > logs/scan.log 2>&1 &
# Stop: kill $(cat logs/scan.pid)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$PROJECT_ROOT/logs/scan.pid"
LOG_FILE="$PROJECT_ROOT/logs/scan.log"

mkdir -p "$PROJECT_ROOT/logs"
echo $$ > "$PID_FILE"

echo "[$(date)] Scan daemon started (PID: $$)" | tee -a "$LOG_FILE"

trap 'echo "[$(date)] Scan daemon stopped" | tee -a "$LOG_FILE"; rm -f "$PID_FILE"' EXIT

while true; do
    echo "[$(date)] === Starting scan cycle ===" >> "$LOG_FILE" 2>&1
    cd "$PROJECT_ROOT"
    python3 scripts/scan/scan_top_800.py --once >> "$LOG_FILE" 2>&1 || true
    echo "[$(date)] === Cycle complete, sleeping 600s ===" >> "$LOG_FILE"
    sleep 600
done
