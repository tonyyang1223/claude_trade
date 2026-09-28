"""全局配置：CORS、百倍币雷达权重、页面元信息等。

颜色与视觉 token 由前端 theme.ts 统一定义；此处仅放后端关心的运行期配置。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

# CORS：开发期 Vite proxy 已覆盖；此处为 prod 预置白名单。
CORS_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
]

APP_NAME = "claude_trading 投研控制台"
APP_VERSION = "0.1.0"

# 实时抓取（web_research）超时（秒）
WEB_RESEARCH_TIMEOUT = 25

# --------------------------------------------------------------------------
# 百倍币雷达启发式权重（初值，可调；与前端 HundredXRadar 共享语义）
# 各维归一化到 0-100；composite 仅对非空维加权并归一。
# --------------------------------------------------------------------------
RADAR_WEIGHTS: Dict[str, float] = {
    "mcapScale": 0.25,
    "growth": 0.25,
    "narrative": 0.20,
    "community": 0.15,
    "onchain": 0.15,
}

# 纳入「小市值加分」的市值上限（USD）；超过则 mcapScale 维度置空。
RADAR_MCAP_CAP = 5_000_000_000.0  # 50 亿

# --------------------------------------------------------------------------
# 历史数据库（DuckDB 单文件）—— 见 docs/history-db/ARCHITECTURE.md §7.3
# --------------------------------------------------------------------------
# 项目根：console/backend/core/config.py → parents[3] = claude_trading
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 历史库数据源开关：
#   'files'  = 默认，保持现状（纯文件直读，老端点零改动）
#   'duckdb' = 走 DuckDB 历史库
#   'auto'   = 存在 DB 且可读则用 duckdb，否则回退 files
HISTORY_SOURCE = os.getenv("CT_HISTORY_SOURCE", "files")

# 历史库（DuckDB）单文件路径；不入版本库，可回填重建（见 .gitignore 的 data/history/）
HISTORY_DB_PATH = PROJECT_ROOT / "data" / "history" / "ct_history.duckdb"
