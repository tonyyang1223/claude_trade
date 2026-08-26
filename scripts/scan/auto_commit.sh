#!/bin/bash
# Auto-commit and push daily scan reports
cd /home/ubuntu/project/claude_trade
git add data/reports
if ! git diff --cached --quiet; then
    git commit -m "docs: 自动更新扫描报告 $(date +%F)"
    git push origin master
fi
