#!/usr/bin/env bash
# 启动后端（FastAPI）。
# 项目根已通过 core.paths 注入 sys.path，可 import src 复用既有分析模块。
set -e
cd "$(dirname "$0")"

echo ">>> 安装依赖（如未安装）"
pip install -r requirements.txt

echo ">>> 启动 uvicorn :8000"
exec uvicorn main:app --host 127.0.0.1 --port 8000 --reload
