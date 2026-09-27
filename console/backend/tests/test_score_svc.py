"""services.score_svc 单元测试 —— 锁死「覆盖率→评级上限」的口径。

背景：``src.analysis.advice.build_advice`` 的 ``coverage`` 契约是**已评分维度的
权重和**（0–1），不是维度个数占比。控制台早期按 ``len(scores)/7`` 估算，在维度
权重不等时会高估覆盖率，从而松开 ``apply_coverage_cap`` 的评级上限（例：真实
0.30 被算成 0.43，上限由 C 松到 B），属安全相关错误。

本测试以伪 Scorer 注入真实 ``ProjectScore``（不触网），锁定三条不变量：
1. typed 路径直接复用 ``ProjectScore.data_coverage``；
2. 维度取自 ``dimension_scores``（不被 typed 路径 ``core(dim, default=3)`` 污染）；
3. legacy 路径 ``data_coverage is None`` → 视为全维覆盖 1.0，评级不被误降级。
"""
import pytest

from services import score_svc

pytest.importorskip("src.data.models", reason="需要项目根 src 可导入（sys.path 由 core.paths 注入）")
from src.data.models import ProjectScore  # noqa: E402


class _FakeScorer:
    """替身 Scorer：直接返回预置 ProjectScore，不触网。"""

    def __init__(self, score: ProjectScore) -> None:
        self._score = score

    def score_project(self, coin_id: str) -> ProjectScore:
        return self._score


def _patch_scorer(monkeypatch, score: ProjectScore) -> None:
    import src.analysis.scorer as scorer_mod

    monkeypatch.setattr(scorer_mod, "Scorer", lambda *a, **k: _FakeScorer(score))


def _typed_score() -> ProjectScore:
    """typed 场景：仅 3 维取到数据，评分器给出真实覆盖率 0.30。"""
    return ProjectScore(
        coin_id="dim3",
        coin_name="Dim3",
        symbol="D3",
        market_score=3,
        technical_score=3,
        onchain_score=3,
        sentiment_score=4,
        github_score=4,
        social_score=4,
        risk_score=3,
        total_score=62.0,
        rating="A",
        recommendation="",
        risk_level="low",
        dimension_scores={"github": 4, "social": 4, "sentiment": 4},
        data_coverage=0.30,
    )


def _legacy_score() -> ProjectScore:
    """legacy 场景：7 维恒有值，data_coverage 未统计（None）。"""
    return ProjectScore(
        coin_id="full7",
        coin_name="Full7",
        symbol="F7",
        market_score=4,
        technical_score=4,
        onchain_score=4,
        sentiment_score=4,
        github_score=4,
        social_score=4,
        risk_score=4,
        total_score=88.0,
        rating="A+",
        recommendation="建议关注",
        risk_level="low",
    )


def test_typed_uses_scorer_coverage_not_dim_count(monkeypatch):
    """关键回归：若按 3/7 估算覆盖率，评级上限会从 C 松到 B（观望→小仓试探）。"""
    _patch_scorer(monkeypatch, _typed_score())

    resp = score_svc.score("dim3")

    assert resp.advice["action"] == "观望"  # rating A 被 0.30 覆盖率压到 C
    assert resp.advice["action"] != "小仓试探"  # 反例：个数占比 0.43 才会得到该动作
    assert resp.advice["positionRange"] == "0–1%"  # C 档 × medium 波动 → 0–1%
    assert resp.advice["disclaimer"], "任何倾向输出都必须带免责声明"


def test_typed_dims_come_from_dimension_scores(monkeypatch):
    """维度应只含真实取到数据的 3 维，不被 default=3 的 *_score 字段污染。"""
    _patch_scorer(monkeypatch, _typed_score())

    resp = score_svc.score("dim3")

    assert set(resp.scores) == {"github", "social", "sentiment"}
    assert resp.scores == {"github": 4.0, "social": 4.0, "sentiment": 4.0}
    assert "market" not in resp.scores  # 该维未取到数据，不应出现


def test_legacy_full_coverage_keeps_rating(monkeypatch):
    """legacy 7 维恒有值 → 覆盖率按 1.0，评级不被降级。"""
    _patch_scorer(monkeypatch, _legacy_score())

    resp = score_svc.score("full7")

    assert len(resp.scores) == 7
    assert resp.advice["action"] == "重点关注"  # A+ 未被覆盖率上限压制
    assert resp.advice["positionRange"] == "5–6%"  # A+×medium=(5,8) 再受 max_position 6% 封顶
    assert resp.advice["horizon"] == "6-12 个月"


def test_scorer_failure_returns_empty_envelope(monkeypatch):
    """Scorer 抛异常时返回空结构而非向上抛（路由据此回 503 信封）。"""
    import src.analysis.scorer as scorer_mod

    def _boom(*a, **k):
        raise RuntimeError("network blocked")

    monkeypatch.setattr(scorer_mod, "Scorer", _boom)

    resp = score_svc.score("whatever")

    assert resp.coinId == "whatever"
    assert resp.scores == {}
    assert resp.advice == {}
