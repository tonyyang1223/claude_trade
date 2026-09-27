"""pytest 配置：把 backend/ 与项目根注入 sys.path。

- backend/：使 core / data / services / routers 包可直接导入。
- 项目根（claude_trading）：使测试可 ``import src``（控制台复用的分析模块）。
  ``core.paths`` 在导入时也会注入项目根，但测试不应依赖「先导入 core」这一隐式顺序，
  故此处显式注入。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(_HERE)
PROJECT_ROOT = os.path.dirname(os.path.dirname(BACKEND_DIR))  # console/backend -> console -> root

for _p in (BACKEND_DIR, PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
