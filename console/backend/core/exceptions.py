"""统一异常 → 信封 {code, message, data}。"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """业务异常基类。

    Attributes:
        code: 信封返回码（非 0）。
        message: 说明文案。
        data: 兜底数据（通常为对应结构的空默认值）。
    """

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class NotFoundError(AppError):
    """数据/日期不存在（对应信封 code=404，但 HTTP 层仍返回 200 信封）。"""

    def __init__(self, message: str = "数据不存在", data: Any = None) -> None:
        super().__init__(404, message, data)


class ServiceUnavailableError(AppError):
    """依赖服务（如 src 网络模块）不可用。"""

    def __init__(self, message: str = "服务暂不可用", data: Any = None) -> None:
        super().__init__(503, message, data)
