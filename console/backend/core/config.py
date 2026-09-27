"""全局配置：CORS、百倍币雷达权重、页面元信息等。

颜色与视觉 token 由前端 theme.ts 统一定义；此处仅放后端关心的运行期配置。
"""
from __future__ import annotations

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

# 默认排序字段（composite / growth / community / mcapScale ...）
RADAR_DEFAULT_SORT = "composite"

RISK_DISCLAIMER = (
    "风险提示：以上仅为基于公开数据的整理，不构成任何投资建议。"
)
