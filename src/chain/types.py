"""链上代币分析的数据模型（Pydantic v2）。

所有五维分析与评分引擎共享这些结构。任意字段为 None 表示「该数据缺失」，
由评分引擎显式跳过（绝不填 0 或 3），与 claude_trading 既有 typed 路径语义一致。

红旗（flags）为结构化 {level, code, msg} 三态（设计文档 §1.2）：level 为
ok/warn/bad，code 为预定义枚举键，展示文案由渲染层从 msg 取。notes 保留
各维度人类可读证据（字符串），与 flags 并存。
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .config import ENGINE_VERSION, AnalysisConfig


class Chain(str, Enum):
    BNB = "bnb"
    SOL = "sol"
    ROBINHOOD = "robinhood"

    @classmethod
    def parse(cls, s: str) -> "Chain":
        s = (s or "").strip().lower()
        aliases = {
            "bnb": cls.BNB, "bsc": cls.BNB, "binance": cls.BNB, "bnbchain": cls.BNB,
            "sol": cls.SOL, "solana": cls.SOL,
            "robinhood": cls.ROBINHOOD, "rh": cls.ROBINHOOD, "robinhoodchain": cls.ROBINHOOD,
        }
        if s in aliases:
            return aliases[s]
        raise ValueError(f"未知链: {s!r}（支持 bnb/sol/robinhood）")


class Flag(BaseModel):
    """结构化欺诈红旗：level 三态 + 机器可读 code + 人类可读 msg。"""
    level: Literal["ok", "warn", "bad"]
    code: str
    msg: str


def flag(level: Literal["ok", "warn", "bad"], code: str, msg: str) -> Flag:
    return Flag(level=level, code=code, msg=msg)


class TokenRef(BaseModel):
    """解析后的代币引用：链 + 合约地址（+ 可选符号/名称）。"""
    chain: Chain
    address: str
    symbol: Optional[str] = None
    name: Optional[str] = None


class HolderStats(BaseModel):
    total_holders: Optional[int] = None
    top10_pct: Optional[float] = None
    top50_pct: Optional[float] = None
    creator_pct: Optional[float] = None
    snipe_pct: Optional[float] = None  # 前 N 个区块内买入占比


class ContractSecurity(BaseModel):
    is_verified: Optional[bool] = None          # 浏览器是否已验证开源
    owner_renounced: Optional[bool] = None      # owner 是否已放弃
    is_mintable: Optional[bool] = None          # 是否仍可增发
    can_take_back_ownership: Optional[bool] = None
    buy_tax_pct: Optional[float] = None
    sell_tax_pct: Optional[float] = None
    hidden_honeypot: Optional[bool] = None       # 模拟卖出是否失败
    is_in_blacklist: Optional[bool] = None       # 是否被列入风险库
    # ---- 字节码扫描得到的特权函数证据（任意 EVM 链通用，无需浏览器 API）----
    is_proxy: Optional[bool] = None              # 是否可升级代理（可换实现 = 后门）
    can_blacklist: Optional[bool] = None         # 是否可拉黑地址
    can_pause: Optional[bool] = None             # 是否可暂停交易
    has_owner_fn: Optional[bool] = None          # 合约是否实现 owner()


class LiquidityInfo(BaseModel):
    total_liquidity_usd: Optional[float] = None
    locked_pct: Optional[float] = None
    locked_until: Optional[str] = None
    is_burned: Optional[bool] = None
    dex: Optional[str] = None


class TokenProfile(BaseModel):
    chain: Chain
    address: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    total_supply: Optional[float] = None
    price_usd: Optional[float] = None
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    fdv: Optional[float] = None
    created_at: Optional[str] = None
    age_days: Optional[float] = None


class DexQuote(BaseModel):
    price_usd: Optional[float] = None
    liquidity_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    buy_sell_ratio: Optional[float] = None       # >1 买方占优（h24 笔数）
    price_change_24h: Optional[float] = None     # 来自所选交易对 h24（与下列多周期一致）
    fdv: Optional[float] = None
    market_cap: Optional[float] = None
    pair_address: Optional[str] = None
    quote_symbol: Optional[str] = None           # 计价代币符号（暴露价格 denominated in 什么）
    # 基础代币身份：无 RPC/浏览器 API 的链（如 Robinhood）profile 为空时，
    # 用 DEX 返回回填 symbol/name，避免报告显示「—」且类别误判为 Uncategorized。
    base_symbol: Optional[str] = None
    base_name: Optional[str] = None
    source: Optional[str] = None
    # ---- Meme 研判扩展字段 ----
    price_changes: Dict[str, float] = Field(default_factory=dict)   # m5/h1/h6/h24 涨跌幅
    txns: Dict[str, Dict[str, Optional[int]]] = Field(default_factory=dict)  # m5/h1/h6/h24 -> {buys,sells}
    age_days: Optional[float] = None             # 交易对创建距今天数（新发代币关键信号）
    socials: List[str] = Field(default_factory=list)   # 官方社媒/渠道链接
    image_url: Optional[str] = None
    price_anomaly: Optional[bool] = None         # price_usd × 总量 与 fdv 严重背离时为 True


class AnalysisResult(BaseModel):
    """一次分析的完整事实载体，贯穿五维分析 → 评分 → 报告。"""
    chain: Chain
    address: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    profile: Optional[TokenProfile] = None
    dex: Optional[DexQuote] = None
    security: Optional[ContractSecurity] = None
    holders: Optional[HolderStats] = None
    liquidity: Optional[LiquidityInfo] = None
    flags: list[Flag] = Field(default_factory=list)          # 结构化红旗 {level,code,msg}
    notes: dict[str, list[str]] = Field(default_factory=dict)  # 各维度证据/结论（人类可读）
    missing: list[str] = Field(default_factory=list)          # 缺失的数据源/维度
    error: Optional[str] = None                               # 致命错误（仅展示用）
    # ---- 元数据（设计文档 §1.2 meta）----
    engine_version: str = ENGINE_VERSION
    fetched_at: Optional[str] = None
    sources_used: list[str] = Field(default_factory=list)
    # ---- 运行时配置槽（仅引擎内传递，不参与序列化）----
    cfg: Optional[AnalysisConfig] = Field(default=None, exclude=True)

    @field_validator("flags", mode="before")
    @classmethod
    def _coerce_legacy_flags(cls, v):
        """向后兼容：历史 dump 的 flags 为字符串数组 → 转结构化 Flag。"""
        if v is None:
            return v
        out = []
        for f in v:
            if isinstance(f, str):
                if f.startswith("🚨"):
                    lvl: Literal["ok", "warn", "bad"] = "bad"
                elif f.startswith("✅"):
                    lvl = "ok"
                else:
                    lvl = "warn"
                out.append({"level": lvl, "code": "LEGACY", "msg": f})
            else:
                out.append(f)
        return out

    def model_dump(self, *args: Any, **kwargs: Any) -> dict:
        """dump 前自动写入分析时间戳（若未设置）。"""
        if self.fetched_at is None:
            self.fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return super().model_dump(*args, **kwargs)
