#!/bin/bash
# Setup crontab for daily data collection
# Usage: sudo bash scripts/setup_cron.sh

set -e

PROJECT_DIR="/home/ubuntu/project/claude_trade"
PYTHON_BIN="/usr/bin/python3"
SCRIPT_PATH="$PROJECT_DIR/scripts/data_collection/daily_collector.py"
LOG_DIR="$PROJECT_DIR/logs"
CRON_USER="ubuntu"

echo "=== Setting up crontab for daily data collection ==="

# Create log directory
mkdir -p "$LOG_DIR"
chown "$CRON_USER:$CRON_USER" "$LOG_DIR"

# Create crontab entry
# Run at 00:05 UTC daily (5 minutes after midnight)
CRON_JOB="5 0 * * * cd $PROJECT_DIR && $PYTHON_BIN $SCRIPT_PATH >> $LOG_DIR/cron.log 2>&1"

# Check if crontab already has this job
if crontab -l 2>/dev/null | grep -q "daily_collector.py"; then
    echo "Crontab entry already exists. Updating..."
    # Remove old entry and add new one
    (crontab -l 2>/dev/null | grep -v "daily_collector.py"; echo "$CRON_JOB") | crontab -
else
    echo "Adding new crontab entry..."
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
fi

# Setup logrotate for collection logs
cat > /etc/logrotate.d/claude_trade_collector << 'EOF'
/home/ubuntu/project/claude_trade/logs/collector.log
/home/ubuntu/project/claude_trade/logs/cron.log
/home/ubuntu/project/claude_trade/logs/whale_monitor.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
EOF

echo "Logrotate config created: /etc/logrotate.d/claude_trade_collector"

# Verify crontab
echo ""
echo "=== Current crontab ==="
crontab -l

echo ""
echo "=== Setup complete ==="
echo "Collection will run daily at 00:05 UTC"
echo "Logs: $LOG_DIR/collector.log and $LOG_DIR/cron.log"
echo ""
echo "To check status, run:"
echo "  python scripts/check_collection_status.py"
