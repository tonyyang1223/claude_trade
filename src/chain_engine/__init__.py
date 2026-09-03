"""chain_engine —— 链上代币取证引擎的稳定公共 API（设计文档 §6 Phase 4 / §7.2）。

跨项目用法（引擎已 `pip install .` 后，任意目录）：
    from chain_engine import analyze, render_markdown, render_json, load_config

仓库内开发态（未安装）同样可用（自动回落 src.chain）。
所有分析路径与 src.chain 完全一致，只是在此收敛公开入口。

保持零业务逻辑：本包仅 re-export + 参数规整，逻辑仍在 src.chain / chain。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _import_backend():
    """优先已安装的顶层 `chain` 包；否则回落仓库内 `src.chain`。"""
    try:
        import chain as _chain_mod  # type: ignore
        return _chain_mod
    except ImportError:
        from src.chain import (  # type: ignore
            AnalysisConfig as AnalysisConfig,
            analyze as _analyze,
            render_html as render_html,
            render_json as render_json,
            render_markdown as render_markdown,
            ENGINE_VERSION,
        )
        return None


def load_config(config: Any = None) -> Any:
    """加载/合并配置：None → 内置默认；dict / YAML 路径 → 覆盖合并。"""
    backend = _import_backend()
    if backend is not None:
        return backend.AnalysisConfig.load(config)
    return AnalysisConfig.load(config)


def analyze(chain: str, query: str, *, rpc: Optional[str] = None,
            api_key: Optional[str] = None, demo: bool = False,
            config: Any = None) -> Tuple[Any, Dict]:
    """统一入口 → (AnalysisResult, decision dict)。"""
    backend = _import_backend()
    if backend is not None:
        return backend.analyze(chain, query, rpc=rpc, api_key=api_key,
                               demo=demo, config=config)
    return _analyze(chain, query, rpc=rpc, api_key=api_key, demo=demo, config=config)


def analyze_dict(chain: str, query: str, *, demo: bool = False,
                 config: Any = None) -> Dict:
    """序列化友好入口：返回可直接 json.dumps 的 dict。"""
    ctx, dec = analyze(chain, query, demo=demo, config=config)
    return {"analysis": ctx.model_dump(), "decision": dec}


def render(result: Any, decision: Dict, fmt: str = "md") -> str:
    """按格式渲染报告（html/md/json）。"""
    backend = _import_backend()
    if fmt == "html":
        fn = backend.render_html if backend is not None else render_html
    elif fmt == "json":
        fn = backend.render_json if backend is not None else render_json
    else:
        fn = backend.render_markdown if backend is not None else render_markdown
    return fn(result, decision)


def version() -> str:
    backend = _import_backend()
    if backend is not None:
        return getattr(backend, "ENGINE_VERSION", "unknown")
    return ENGINE_VERSION


__all__ = ["analyze", "analyze_dict", "render", "load_config", "version"]
