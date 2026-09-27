"""E1 /api/health、/api/meta —— 健康检查与数据元信息（纯本地）。"""
from __future__ import annotations

from fastapi import APIRouter

from core.config import APP_VERSION, RADAR_WEIGHTS
from core.envelope import success
from data import loader
from data.schemas import HealthResponse, MetaResponse
from services.market_svc import build_meta

router = APIRouter(tags=["meta"])


@router.get("/api/health")
async def health() -> dict:
    date = loader.resolve_scan_date(None)
    return success(HealthResponse(status="ok", version=APP_VERSION, dataDate=date).model_dump())


@router.get("/api/meta")
async def meta() -> dict:
    date = loader.resolve_scan_date(None)
    base = build_meta(date)
    base["availableDates"] = loader.list_scan_dates()
    base["weights"] = RADAR_WEIGHTS
    return success(MetaResponse(**{
        "date": base.get("date"),
        "prevDay": base.get("prevDay"),
        "scanTime": base.get("scanTime"),
        "deepTotal": base.get("deepTotal"),
        "lightTotal": base.get("lightTotal"),
        "coinCnt": base.get("coinCnt"),
        "availableDates": base.get("availableDates"),
        "weights": base.get("weights"),
    }).model_dump())
