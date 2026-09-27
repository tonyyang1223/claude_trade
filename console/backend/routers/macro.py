"""E9 GET /api/macro/btc-dominance —— BTC 占比与市场规模判断（best-effort）。

注意命名：处理函数**不可**再叫 ``btc_dominance``——那会在模块级覆盖同名 service 导入，
使函数体里的 ``btc_dominance()`` 递归调用自身（返回 coroutine → AttributeError → 500）。
"""
from __future__ import annotations

from fastapi import APIRouter

from core.envelope import failure, success
from services.macro_svc import btc_dominance as fetch_btc_dominance

router = APIRouter(tags=["macro"])


@router.get("/api/macro/btc-dominance")
def btc_dominance() -> dict:
    data = fetch_btc_dominance()
    if not data.currentDominance:
        return failure(503, "BTC 占比暂不可用（可能为网络受限）", data.model_dump())
    return success(data.model_dump(), message="ok")
