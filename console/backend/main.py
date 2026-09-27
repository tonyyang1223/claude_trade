"""FastAPI 应用入口。

启动:
    cd console/backend && pip install -r requirements.txt
    uvicorn main:app --port 8000 --reload

设计要点:
- 项目根已通过 ``core.paths`` 注入 ``sys.path``，可 ``import src`` 复用既有分析模块。
- 所有响应走统一信封 {code,message,data}；全局异常处理器把任意未捕获异常
  转换为信封（code != 0），**绝不向客户端抛出 500**。
- 分析类端点（src 网络模块）在 service 层 try/except 包裹，失败返回空结构 + message。
"""
from __future__ import annotations

import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 必须最先导入，确保 sys.path 注入项目根（import src 可用）
from core import paths  # noqa: F401
from core.config import APP_NAME, APP_VERSION, CORS_ORIGINS
from core.envelope import EnvelopeResponse
from core.exceptions import AppError

from routers import meta, market, tokens, opportunity, compare, chain, scores, macro, research

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="加密货币量化投研控制台后端（FastAPI + 复用 src 分析模块）",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> EnvelopeResponse:
    """业务异常 → 信封（保留原始 HTTP 200，交由前端解析 code）。"""
    return EnvelopeResponse(data=exc.data, message=exc.message, code=exc.code, status_code=200)


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> EnvelopeResponse:
    """未捕获异常 → 信封（绝不 500）。记录堆栈便于排查。"""
    tb = traceback.format_exc()
    print(f"[ERROR] 未捕获异常 {request.method} {request.url.path}:\n{tb}")
    return EnvelopeResponse(
        data=None,
        message=f"服务器内部错误: {exc}",
        code=500,
        status_code=200,
    )


@app.get("/")
async def root() -> dict:
    return {"code": 0, "message": "ok", "data": {"name": APP_NAME, "version": APP_VERSION}}


# 挂载路由
app.include_router(meta.router)
app.include_router(market.router)
app.include_router(tokens.router)
app.include_router(opportunity.router)
app.include_router(compare.router)
app.include_router(chain.router)
app.include_router(scores.router)
app.include_router(macro.router)
app.include_router(research.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
