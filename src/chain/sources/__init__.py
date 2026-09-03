"""第三方数据源接入层（DEX 价格 / 安全审计）。

与 adapters 的职责边界：adapters = 链原生 RPC/浏览器；sources = 第三方聚合。
所有函数返回 Optional，失败时返回 None，由编排层降级，绝不抛异常。
"""
from .dexscreener import get_quote, search_token
from .goplus import get_security, get_security_full

__all__ = ["get_quote", "search_token", "get_security", "get_security_full"]
