"""tests/chain 共享夹具：把仓库根加入 sys.path，保证 `import src.chain` 可用。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 允许 test_*.py 便捷构建合成上下文
from src.chain.types import (  # noqa: E402, F401
    AnalysisResult,
    Chain,
    ContractSecurity,
    DexQuote,
    HolderStats,
    LiquidityInfo,
    TokenProfile,
)

REPO_ROOT = ROOT
CHAIN_CONFIG_DIR = REPO_ROOT / "config" / "chain"
