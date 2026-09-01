"""代币与 DeFi 协议研究模块（Token & DeFi Research）。

把「代币经济 / 估值 / 解锁抛压 / 协议对比」这套研究框架落地为可复用代码，
复用项目已有的 :class:`src.api.coingecko.CoinGeckoClient` 与
:class:`src.api.defillama.DefiLlamaClient`，不重复造 HTTP 请求层。

设计约定：

- **纯函数与取数分离**：所有指标计算（流通率、稀释倍数、P/S、解锁风险分档）
  都是无网络依赖的纯函数，便于单元测试；网络调用集中在 ``TokenDefiResearcher``。
- **不编造数据**：取不到的字段一律为 ``None``，由调用方决定如何展示，
  绝不用占位数字冒充真实数据。
- **口径显式**：P/S 区分 FDV 口径与市值口径；费用区分 24h / 30d / 年化。

Example:
    >>> from src.research.token_defi import TokenDefiResearcher
    >>> researcher = TokenDefiResearcher()
    >>> token = researcher.analyze_token("ethena")
    >>> round(token.circulating_ratio, 3)
    0.655
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.api.coingecko import CoinGeckoClient
from src.api.defillama import DefiLlamaClient

__all__ = [
    "circulating_ratio",
    "dilution_multiple",
    "locked_supply",
    "fdv_mc_ratio",
    "price_to_sales",
    "fee_to_tvl",
    "unlock_risk_level",
    "TokenSnapshot",
    "ProtocolSnapshot",
    "UnlockProfile",
    "TokenDefiResearcher",
]

SOURCE_COINGECKO = "CoinGecko"
SOURCE_DEFILLAMA = "DefiLlama"

# 解锁风险分档阈值（按待解锁占比 locked_ratio）
UNLOCK_RISK_HIGH = 0.50
UNLOCK_RISK_MEDIUM = 0.30


# --------------------------------------------------------------------------
# 纯计算函数（无网络依赖，可直接单元测试）
# --------------------------------------------------------------------------

def circulating_ratio(
    circulating: Optional[float],
    total_supply: Optional[float],
    max_supply: Optional[float],
) -> Optional[float]:
    """计算流通率 = 流通量 / (最大供应量 or 总供应量)。

    Args:
        circulating: 当前流通量
        total_supply: 总供应量
        max_supply: 最大供应量（优先作为分母）

    Returns:
        流通率（0~1）；分母缺失或为 0 时返回 None
    """
    denominator = max_supply or total_supply
    if not circulating or not denominator:
        return None
    return circulating / denominator


def dilution_multiple(
    circulating: Optional[float],
    total_supply: Optional[float],
    max_supply: Optional[float],
) -> Optional[float]:
    """计算稀释倍数 = (最大供应量 or 总供应量) / 流通量。

    表示若全部解锁，流通盘将被放大的倍数（1.5× 即还有 50% 增量供给）。

    Args:
        circulating: 当前流通量
        total_supply: 总供应量
        max_supply: 最大供应量（优先作为分子）

    Returns:
        稀释倍数；输入缺失时返回 None
    """
    numerator = max_supply or total_supply
    if not numerator or not circulating:
        return None
    return numerator / circulating


def locked_supply(
    circulating: Optional[float],
    total_supply: Optional[float],
    max_supply: Optional[float],
) -> Optional[float]:
    """计算待解锁量 = (最大供应量 or 总供应量) - 流通量。

    Args:
        circulating: 当前流通量
        total_supply: 总供应量
        max_supply: 最大供应量

    Returns:
        待解锁代币数量；输入缺失时返回 None
    """
    numerator = max_supply or total_supply
    if numerator is None or circulating is None:
        return None
    return max(numerator - circulating, 0.0)


def fdv_mc_ratio(fdv: Optional[float], market_cap: Optional[float]) -> Optional[float]:
    """计算 FDV/MC 倍数，衡量未来稀释空间。

    Args:
        fdv: 完全稀释估值
        market_cap: 当前市值

    Returns:
        FDV/MC；市值缺失或为 0 时返回 None
    """
    if not fdv or not market_cap:
        return None
    return fdv / market_cap


def price_to_sales(
    valuation: Optional[float], annual_fees: Optional[float]
) -> Optional[float]:
    """计算 P/S = 估值 / 年化费用。

    Args:
        valuation: 估值口径（FDV 或市值，需与比较对象保持一致）
        annual_fees: 年化协议费用

    Returns:
        P/S 倍数；费用缺失或为 0 时返回 None（避免除零与无意义倍数）
    """
    if not valuation or not annual_fees:
        return None
    return valuation / annual_fees


def fee_to_tvl(annual_fees: Optional[float], tvl: Optional[float]) -> Optional[float]:
    """计算资本效率 = 年化费用 / TVL，衡量每单位锁仓创造的费用。

    Args:
        annual_fees: 年化协议费用
        tvl: 协议锁仓量

    Returns:
        费用/TVL 比率；TVL 缺失或为 0 时返回 None
    """
    if not annual_fees or not tvl:
        return None
    return annual_fees / tvl


def unlock_risk_level(locked_ratio: Optional[float]) -> str:
    """按待解锁占比给出解锁风险分档。

    Args:
        locked_ratio: 待解锁占比（0~1）

    Returns:
        '高' / '中' / '低' / '未知'（数据缺失时）
    """
    if locked_ratio is None:
        return "未知"
    if locked_ratio >= UNLOCK_RISK_HIGH:
        return "高"
    if locked_ratio >= UNLOCK_RISK_MEDIUM:
        return "中"
    return "低"


# --------------------------------------------------------------------------
# 数据结构
# --------------------------------------------------------------------------

@dataclass
class TokenSnapshot:
    """单个代币的研究快照（代币经济 + 估值 + 涨跌）。

    Attributes:
        coin_id: CoinGecko 代币 ID
        symbol: 代币符号
        name: 代币名称
        categories: 所属赛道/标签
        price: 当前价格（USD）
        market_cap: 市值（USD）
        fdv: 完全稀释估值（USD）
        circulating_supply: 流通量
        total_supply: 总供应量
        max_supply: 最大供应量
        circulating_ratio: 流通率
        locked_supply: 待解锁量
        locked_ratio: 待解锁占比
        dilution_multiple: 稀释倍数
        fdv_mc_ratio: FDV/MC
        change_24h / change_7d / change_30d: 涨跌幅（%）
        ath: 历史最高价
        ath_change_pct: 距 ATH 回撤（%）
        source: 数据来源
        fetched_at: 抓取时间（UTC ISO）
    """

    coin_id: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    price: Optional[float] = None
    market_cap: Optional[float] = None
    fdv: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    circulating_ratio: Optional[float] = None
    locked_supply: Optional[float] = None
    locked_ratio: Optional[float] = None
    dilution_multiple: Optional[float] = None
    fdv_mc_ratio: Optional[float] = None
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    change_30d: Optional[float] = None
    ath: Optional[float] = None
    ath_change_pct: Optional[float] = None
    source: str = SOURCE_COINGECKO
    fetched_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（便于 JSON 序列化）。"""
        return asdict(self)


@dataclass
class ProtocolSnapshot:
    """单个 DeFi 协议的研究快照（TVL + 费用 + 估值 + 关联代币）。

    Attributes:
        slug: DefiLlama 协议 slug
        name: 协议名称
        tvl: 当前锁仓量（USD）
        tvl_change_24h / tvl_change_7d: TVL 变化（%）
        chain_breakdown: 各链 TVL 分布
        fees_24h / fees_30d / fees_annualized / fees_all_time: 费用（USD）
        fee_to_tvl: 资本效率（年化费用 / TVL）
        token: 关联治理代币快照（可为空）
        ps_fdv: P/S（FDV 口径）
        ps_mcap: P/S（市值口径）
        source: 数据来源
        fetched_at: 抓取时间（UTC ISO）
    """

    slug: str
    name: Optional[str] = None
    tvl: Optional[float] = None
    tvl_change_24h: Optional[float] = None
    tvl_change_7d: Optional[float] = None
    chain_breakdown: Dict[str, float] = field(default_factory=dict)
    fees_24h: Optional[float] = None
    fees_30d: Optional[float] = None
    fees_annualized: Optional[float] = None
    fees_all_time: Optional[float] = None
    fee_to_tvl: Optional[float] = None
    token: Optional[TokenSnapshot] = None
    ps_fdv: Optional[float] = None
    ps_mcap: Optional[float] = None
    source: str = SOURCE_DEFILLAMA
    fetched_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（嵌套 token 一并展开）。"""
        data = asdict(self)
        data["token"] = self.token.to_dict() if self.token else None
        return data


@dataclass
class UnlockProfile:
    """单个代币的解锁抛压画像。

    Attributes:
        coin_id: CoinGecko 代币 ID
        symbol: 代币符号
        circulating_supply: 流通量
        total_supply: 总供应量
        max_supply: 最大供应量
        circulating_ratio: 流通率
        locked_supply: 待解锁量
        locked_ratio: 待解锁占比
        dilution_multiple: 稀释倍数
        risk_level: 解锁风险分档（高/中/低/未知）
        market_cap: 市值（用于估算解锁名义规模）
    """

    coin_id: str
    symbol: Optional[str] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    circulating_ratio: Optional[float] = None
    locked_supply: Optional[float] = None
    locked_ratio: Optional[float] = None
    dilution_multiple: Optional[float] = None
    risk_level: str = "未知"
    market_cap: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return asdict(self)


# --------------------------------------------------------------------------
# 研究器（封装网络调用）
# --------------------------------------------------------------------------

class TokenDefiResearcher:
    """代币与 DeFi 协议研究器。

    组合项目现有的两个 API 客户端，产出结构化研究快照。
    所有指标计算委托给模块级纯函数，保证可测试性。

    Attributes:
        coingecko: CoinGecko 客户端
        defillama: DefiLlama 客户端

    Example:
        >>> researcher = TokenDefiResearcher()
        >>> profiles = researcher.unlock_profiles(["arbitrum", "ethena"])
        >>> [p.risk_level for p in profiles]
        ['中', '中']
    """

    def __init__(
        self,
        coingecko: Optional[CoinGeckoClient] = None,
        defillama: Optional[DefiLlamaClient] = None,
    ) -> None:
        """初始化研究器。

        Args:
            coingecko: CoinGecko 客户端（默认新建，可注入 mock 便于测试）
            defillama: DefiLlama 客户端（默认新建，可注入 mock 便于测试）
        """
        self.coingecko = coingecko or CoinGeckoClient()
        self.defillama = defillama or DefiLlamaClient()

    @staticmethod
    def _now() -> str:
        """返回当前 UTC 时间（ISO 格式）。"""
        return datetime.now(timezone.utc).isoformat()

    def analyze_token(self, coin_id: str) -> TokenSnapshot:
        """分析单个代币的代币经济、估值与涨跌。

        Args:
            coin_id: CoinGecko 代币 ID（如 'ethena'、'bitcoin'）

        Returns:
            TokenSnapshot；取数失败时字段为 None，不填充占位值
        """
        raw = self.coingecko.get_coin_research_data(coin_id)

        circulating = raw.get("circulating_supply")
        total_supply = raw.get("total_supply")
        max_supply = raw.get("max_supply")

        ratio = circulating_ratio(circulating, total_supply, max_supply)

        return TokenSnapshot(
            coin_id=coin_id,
            symbol=raw.get("symbol"),
            name=raw.get("name"),
            categories=raw.get("categories") or [],
            price=raw.get("price"),
            market_cap=raw.get("market_cap"),
            fdv=raw.get("fdv"),
            circulating_supply=circulating,
            total_supply=total_supply,
            max_supply=max_supply,
            circulating_ratio=ratio,
            locked_supply=locked_supply(circulating, total_supply, max_supply),
            locked_ratio=(1 - ratio) if ratio is not None else None,
            dilution_multiple=dilution_multiple(circulating, total_supply, max_supply),
            fdv_mc_ratio=fdv_mc_ratio(raw.get("fdv"), raw.get("market_cap")),
            change_24h=raw.get("change_24h"),
            change_7d=raw.get("change_7d"),
            change_30d=raw.get("change_30d"),
            ath=raw.get("ath"),
            ath_change_pct=raw.get("ath_change_pct"),
            source=SOURCE_COINGECKO,
            fetched_at=raw.get("last_updated") or self._now(),
        )

    def analyze_protocol(
        self, slug: str, coin_id: Optional[str] = None
    ) -> ProtocolSnapshot:
        """分析单个 DeFi 协议的 TVL、费用与估值。

        Args:
            slug: DefiLlama 协议 slug（如 'uniswap'、'curve-dex'）
            coin_id: 关联治理代币 ID（如 'uniswap'、'curve-dao-token'）；
                传入后会一并返回代币快照与 P/S

        Returns:
            ProtocolSnapshot
        """
        tvl_data = self.defillama.get_protocol_tvl(slug)
        fee_data = self.defillama.get_protocol_fees(slug)

        annual_fees = fee_data.get("fees_annualized")
        tvl = tvl_data.get("tvl")

        token: Optional[TokenSnapshot] = None
        ps_fdv: Optional[float] = None
        ps_mcap: Optional[float] = None

        if coin_id:
            token = self.analyze_token(coin_id)
            ps_fdv = price_to_sales(token.fdv, annual_fees)
            ps_mcap = price_to_sales(token.market_cap, annual_fees)

        return ProtocolSnapshot(
            slug=slug,
            name=tvl_data.get("protocol") or slug,
            tvl=tvl,
            tvl_change_24h=tvl_data.get("tvl_change_24h"),
            tvl_change_7d=tvl_data.get("tvl_change_7d"),
            chain_breakdown=tvl_data.get("chain_breakdown") or {},
            fees_24h=fee_data.get("fees_24h"),
            fees_30d=fee_data.get("fees_30d"),
            fees_annualized=annual_fees,
            fees_all_time=fee_data.get("fees_all_time"),
            fee_to_tvl=fee_to_tvl(annual_fees, tvl),
            token=token,
            ps_fdv=ps_fdv,
            ps_mcap=ps_mcap,
            source=SOURCE_DEFILLAMA,
            fetched_at=self._now(),
        )

    def compare_protocols(
        self, targets: Sequence[Dict[str, str]]
    ) -> List[ProtocolSnapshot]:
        """批量对比多个协议。

        Args:
            targets: 协议列表，每项为 ``{"slug": ..., "coin_id": ...}``，
                其中 ``coin_id`` 可选

        Returns:
            ProtocolSnapshot 列表（顺序与输入一致）
        """
        return [
            self.analyze_protocol(
                slug=item["slug"], coin_id=item.get("coin_id")
            )
            for item in targets
        ]

    def unlock_profiles(self, coin_ids: Sequence[str]) -> List[UnlockProfile]:
        """批量生成代币解锁抛压画像。

        Args:
            coin_ids: CoinGecko 代币 ID 列表

        Returns:
            UnlockProfile 列表；单个代币取数失败会被跳过（不中断整体）

        Note:
            这里只用「流通率 / 待解锁占比」这类供应量硬数据；
            精确的逐日解锁日历与 cliff 日期需 TokenUnlocks（需 key）或项目公告。
        """
        profiles: List[UnlockProfile] = []

        for coin_id in coin_ids:
            try:
                snapshot = self.analyze_token(coin_id)
            except Exception as exc:  # pragma: no cover - 依赖网络
                print(f"Warning: 跳过 {coin_id}（取数失败: {exc}）")
                continue

            profiles.append(
                UnlockProfile(
                    coin_id=coin_id,
                    symbol=snapshot.symbol,
                    circulating_supply=snapshot.circulating_supply,
                    total_supply=snapshot.total_supply,
                    max_supply=snapshot.max_supply,
                    circulating_ratio=snapshot.circulating_ratio,
                    locked_supply=snapshot.locked_supply,
                    locked_ratio=snapshot.locked_ratio,
                    dilution_multiple=snapshot.dilution_multiple,
                    risk_level=unlock_risk_level(snapshot.locked_ratio),
                    market_cap=snapshot.market_cap,
                )
            )

        return profiles
