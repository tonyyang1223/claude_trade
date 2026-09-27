"""统一响应信封 {code, message, data}。

所有 API 返回结构一致：
- code: 0=成功；非 0 见各端点约定（404=日期/数据不存在返回空结构；5xx=内部错误经异常处理转信封）。
- message: 人类可读说明。
- data: 业务数据（数据缺失时返回该结构的空默认值，绝不抛 500）。
"""
from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success(data: Any = None, message: str = "ok") -> dict:
    """构造成功信封。"""
    return {"code": 0, "message": message, "data": data}


def failure(code: int, message: str, data: Any = None) -> dict:
    """构造失败信封（非 0 code）。"""
    return {"code": code, "message": message, "data": data}


class EnvelopeResponse(JSONResponse):
    """直接以信封结构返回的 JSONResponse。"""

    def __init__(
        self,
        data: Any = None,
        message: str = "ok",
        code: int = 0,
        status_code: int = 200,
        **kwargs,
    ) -> None:
        payload = {"code": code, "message": message, "data": jsonable_encoder(data)}
        super().__init__(content=payload, status_code=status_code, **kwargs)
