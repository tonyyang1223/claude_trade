"""历史数据仓储层：文件直读 ↔ DuckDB 双读，产出同一结构 —— 见 ARCHITECTURE.md §7。

设计目标：``services/*`` 与 ``routers/*`` **零改动**；``data/loader.py`` 退化为 facade，
把所有公开读取函数委托到本模块的 ``get_repository()``。两个实现（``FileRepository`` /
``DuckDBRepository``）对同一输入产出**结构等价**的 Python 对象。

回退链（§7.4，四级，全部对 ``services`` 透明）：
1. 未安装 duckdb（``HAS_DUCKDB`` guard）；
2. DB 文件不存在 / 只读打开失败；
3. 目标日期在 DB 中无任何行 → **请求级**回退文件（保证老端点不返回空）；
4. ``CT_HISTORY_SOURCE=files`` 人工强制。

关键约定：``DuckDBRepository`` 的所有读取路径都包在 ``try/except`` 内，
失败即内部转调 ``FileRepository``，**绝不向上冒泡异常**（契合「绝不抛 500」）。
"""
from __future__ import annotations

import glob
import json
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol

from core import paths
from core.config import HISTORY_DB_PATH, HISTORY_SOURCE
from data import duck


# --------------------------------------------------------------------------
# 纯文件工具（与 loader.load_json 同语义，延迟导入以复用单一实现、避免循环依赖）
# --------------------------------------------------------------------------
def _read_json(path: str) -> Optional[Any]:
    """读取 JSON 文件（失败返回 None，绝不抛异常）。

    复用 ``loader.load_json`` 的既有语义，延迟导入避免 ``loader ↔ repository`` 循环导入。
    """
    from data.loader import load_json

    return load_json(path)


def is_valid_date(date: str) -> bool:
    """``date`` 是否为可解析的 ``YYYY-MM-DD``（外部入参 ``?date=`` 未做格式校验）。"""
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# 仓储协议
# --------------------------------------------------------------------------
class HistoryRepository(Protocol):
    """历史数据仓储协议：文件直读与 DuckDB 读取共同实现它。"""

    def resolve_scan_date(self, date: Optional[str] = None) -> Optional[str]:
        """解析扫描日期；``None``/``latest`` 取最新可用日。"""
        ...

    def list_scan_dates(self) -> List[str]:
        """全部可用扫描日期（升序）。"""
        ...

    def load_summary(self, date: str) -> Optional[dict]:
        """读取某日 ``summary.json`` 同构 dict。"""
        ...

    def load_all_coins(self, date: str) -> List[dict]:
        """读取 ``top_800_light`` 全部币（按 id 去重、price_usd 非空）。"""
        ...

    def load_by_category_raw(self, date: str) -> Dict[str, List[dict]]:
        """读取 ``by_category``：``{slug: [成员 dict, ...]}``（含 7 日窗口解析）。"""
        ...

    def load_deep_raw(self, date: str) -> Dict[str, dict]:
        """读取 ``top_50_detailed``：``{coin_id: 原始 dict}``（含次日填充）。"""
        ...

    def find_coin_raw(self, date: str, coin_id: str) -> Optional[dict]:
        """定位某币原始记录（deep 优先，by_category 兜底）。"""
        ...


# --------------------------------------------------------------------------
# FileRepository：纯文件直读（逻辑原样取自旧 loader.py）
# --------------------------------------------------------------------------
class FileRepository:
    """文件直读仓储。**路径一律在调用时动态读取 ``paths.DAILY_SCAN_DIR``**，
    绝不在实例化/导入时固化——否则 ``monkeypatch.setattr(paths, "DAILY_SCAN_DIR", ...)``
    之类的测试替换会失效（见 tests/test_loader.py）。
    """

    def resolve_scan_date(self, date: Optional[str] = None) -> Optional[str]:
        return paths.resolve_scan_date(date)

    def list_scan_dates(self) -> List[str]:
        return paths.list_scan_dates()

    # ---- 内部路径辅助（动态读取，不做任何缓存） ----
    @staticmethod
    def _day_dir(date: str) -> str:
        return str(paths.DAILY_SCAN_DIR / date)

    @staticmethod
    def _scan_days() -> List[str]:
        """扫描目录下的条目名（升序）。目录不存在/不可读时返回空而非抛异常。"""
        try:
            return sorted(os.listdir(paths.DAILY_SCAN_DIR))
        except OSError as exc:  # noqa: BLE001
            print(f"[repository] 扫描目录不可读 {paths.DAILY_SCAN_DIR}: {exc}")
            return []

    def load_summary(self, date: str) -> Optional[dict]:
        return _read_json(os.path.join(self._day_dir(date), "summary.json"))

    def load_all_coins(self, date: str) -> List[dict]:
        """读取 top_800_light 全部币，按 id 去重（与 build_dashboard 口径一致）。"""
        fp = os.path.join(self._day_dir(date), "top_800_light", "all_coins.json")
        coins = _read_json(fp)
        if not coins:
            return []
        seen: set = set()
        out: List[dict] = []
        for c in coins:
            cid = c.get("id")
            if not cid or c.get("price_usd") is None or cid in seen:
                continue
            seen.add(cid)
            c["change_24h_pct"] = c.get("change_24h_pct") or 0.0
            c["change_7d_pct"] = c.get("change_7d_pct") or 0.0
            out.append(c)
        return out

    def load_by_category_raw(self, date: str) -> Dict[str, List[dict]]:
        """读取 by_category：``{cat: [原始 json 记录...]}``。

        按 build_dashboard 口径：优先取近 7 天内**覆盖币数最多**的一天
        （并列取较晚者）。``date`` 非法时跳过窗口扫描，直接用 ``date`` 当日目录。
        """
        cat_dir = os.path.join(self._day_dir(date), "by_category")

        if is_valid_date(date):
            best_cnt = -1
            min_day = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
            for d in reversed(self._scan_days()):  # 降序遍历：并列取较晚者
                if d < min_day:
                    continue
                p = os.path.join(str(paths.DAILY_SCAN_DIR), d, "by_category")
                if os.path.isdir(p):
                    cnt = sum(len(files) for _, _, files in os.walk(p))
                    if cnt > best_cnt:
                        cat_dir, best_cnt = p, cnt
        else:
            print(f"[repository] 非法日期 {date!r}，跳过 by_category 7 日窗口扫描")

        result: Dict[str, List[dict]] = {}
        if not os.path.isdir(cat_dir):
            return result
        for cat in sorted(os.listdir(cat_dir)):
            files = glob.glob(os.path.join(cat_dir, cat, "*.json"))
            members: List[dict] = []
            for fp in files:
                j = _read_json(fp)
                if j:
                    members.append(j)
            if members:
                result[cat] = members
        return result

    def load_deep_raw(self, date: str) -> Dict[str, dict]:
        """读取 top_50_detailed：``{coin_id: 原始 json}``，当日优先、合并**次日**。

        历史实现（保持逐字等价）：在升序扫描日中取 ``date`` 的下一日做「填充」，
        请求当日覆盖次日（``deep[cid] = j``）。
        """
        root = str(paths.DAILY_SCAN_DIR)
        days = self._scan_days()
        next_day: Optional[str] = None
        if date in days:
            i = days.index(date)
            next_day = days[i + 1] if i + 1 < len(days) else None

        deep: Dict[str, dict] = {}
        for d in ([next_day, date] if next_day else [date]):
            dd = os.path.join(root, d, "top_50_detailed")
            if not os.path.isdir(dd):
                continue
            for fp in glob.glob(os.path.join(dd, "*.json")):
                j = _read_json(fp)
                if not j:
                    continue
                cid = j.get("coin_id")
                if cid:
                    deep[cid] = j  # 当日覆盖次日
        return deep

    def find_coin_raw(self, date: str, coin_id: str) -> Optional[dict]:
        """在 top_50_detailed 与 by_category 中定位某币原始记录。"""
        # 1) top_50_detailed/<id>.json（精确当日，不做次日合并）
        fp = os.path.join(self._day_dir(date), "top_50_detailed", f"{coin_id}.json")
        j = _read_json(fp)
        if j:
            return j
        # 2) 在 by_category 各文件里找 coin_id 匹配
        raw = self.load_by_category_raw(date)
        for members in raw.values():
            for m in members:
                if m.get("coin_id") == coin_id:
                    return m
        return None


# --------------------------------------------------------------------------
# DuckDBRepository：查历史库，产出与 FileRepository 同构的对象
# --------------------------------------------------------------------------
class DuckDBRepository:
    """DuckDB 读取仓储。

    - 任何读取失败（异常 / 目标日无行）都内部回退 ``FileRepository``；
    - 结果与文件直读**逐字段同构**（列名映射回源字段名，如 ``coin_id`` → ``id``）。
    """

    # ``coin_daily_snapshot`` 中与 ``top_800_light`` 源字段一一对应的列
    # （列名 = 源字段名；``coin_id``/``snapshot_ts`` 需映射回 ``id``/``timestamp``）
    _SNAPSHOT_COLS: tuple = (
        "coin_id", "symbol", "name", "rank", "price_usd", "market_cap", "volume_24h",
        "change_24h_pct", "change_7d_pct", "circulating_supply", "total_supply",
        "max_supply", "snapshot_ts",
    )

    def __init__(self, db_path: Any) -> None:
        self.db_path = db_path
        self._files = FileRepository()  # 回退实现（组合，非继承）

    # ---- 连接 / 查询辅助 ----
    @staticmethod
    def _conn() -> Any:
        return duck.read_conn()

    def _fetchall(self, sql: str, params: Optional[List[Any]] = None) -> List[tuple]:
        conn = self._conn()
        cur = conn.execute(sql, params) if params is not None else conn.execute(sql)
        return cur.fetchall()

    # ---- 读接口 ----
    def resolve_scan_date(self, date: Optional[str] = None) -> Optional[str]:
        if date and date != "latest":
            return date  # 与文件版一致：显式日期原样返回（不校验存在性）
        try:
            rows = self._fetchall("SELECT MAX(date) FROM scan_day")
            if rows and rows[0][0] is not None:
                return _fmt_date(rows[0][0])
        except Exception as exc:  # noqa: BLE001 - 回退路径不得冒泡
            print(f"[DuckDBRepository] resolve_scan_date 失败，回退文件：{exc}")
        return self._files.resolve_scan_date(date)

    def list_scan_dates(self) -> List[str]:
        try:
            rows = self._fetchall("SELECT date FROM scan_day ORDER BY date")
            if rows:
                return [_fmt_date(r[0]) for r in rows if r[0] is not None]
        except Exception as exc:  # noqa: BLE001
            print(f"[DuckDBRepository] list_scan_dates 失败，回退文件：{exc}")
        return self._files.list_scan_dates()

    def load_summary(self, date: str) -> Optional[dict]:
        """从 ``scan_day`` 重建与 ``summary.json`` 同构的 dict。

        Note:
            仅能重建 ``scan_day`` 持久化的字段（``scan_time`` / ``total_coins`` /
            ``deep_researched`` / ``light_researched`` / ``categories`` /
            ``market_stats`` / ``state_stats``）。源 ``summary.json`` 里可能存在的
            ``highlights`` / ``elapsed_seconds`` / ``top_50_detailed`` / ``top_800_light``
            **未入库**（架构 §4 未落这些列），且时间戳被归一为**秒级**；这些字段不被任何
            端点消费，故端点输出不受影响。目标日无行时回退文件。
        """
        try:
            rows = self._fetchall(
                """
                SELECT scan_time, total_coins, deep_researched_decl, light_researched_decl,
                       categories_json, market_stats_json, state_stats_json
                  FROM scan_day WHERE date = ?::DATE
                """,
                [date],
            )
            if not rows:
                return self._files.load_summary(date)
            (scan_time, total_coins, deep_decl, light_decl,
             categories_json, market_stats_json, state_stats_json) = rows[0]
            out: Dict[str, Any] = {
                "scan_time": _fmt_ts(scan_time),
                "total_coins": total_coins,
                "deep_researched": deep_decl,
                "light_researched": light_decl,
                "categories": _loads(categories_json),
                "market_stats": _loads(market_stats_json),
            }
            if state_stats_json is not None:
                out["state_stats"] = _loads(state_stats_json)
            return out
        except Exception as exc:  # noqa: BLE001
            print(f"[DuckDBRepository] load_summary 失败，回退文件：{exc}")
            return self._files.load_summary(date)

    def load_all_coins(self, date: str) -> List[dict]:
        """查 ``coin_daily_snapshot``，映射回 ``top_800_light`` 源字段名。

        ``coin_id`` → ``id``、``snapshot_ts`` → ``timestamp``（ISO 秒级）；
        ``change_24h_pct`` / ``change_7d_pct`` 缺失时补 0.0（与文件版口径一致）。
        ``ORDER BY rowid`` 复现「按源文件顺序」的确定性输出。
        """
        sql = (
            f"SELECT {', '.join(self._SNAPSHOT_COLS)} FROM coin_daily_snapshot "
            "WHERE date = ?::DATE ORDER BY rowid"
        )
        try:
            rows = self._fetchall(sql, [date])
            if not rows:
                return self._files.load_all_coins(date)  # 目标日无行 → 请求级回退
            out: List[dict] = []
            for row in rows:
                rec = dict(zip(self._SNAPSHOT_COLS, row))
                rec["id"] = rec.pop("coin_id")
                ts = rec.pop("snapshot_ts")
                rec["timestamp"] = _fmt_ts(ts)
                rec["change_24h_pct"] = rec.get("change_24h_pct") or 0.0
                rec["change_7d_pct"] = rec.get("change_7d_pct") or 0.0
                out.append(rec)
            return out
        except Exception as exc:  # noqa: BLE001
            print(f"[DuckDBRepository] load_all_coins 失败，回退文件：{exc}")
            return self._files.load_all_coins(date)

    def load_by_category_raw(self, date: str) -> Dict[str, List[dict]]:
        """复刻「7 日窗口取最大成员数」解析，并重建成员 dict。

        解析 SQL（§7.2）：在 ``[date-7, date]`` 内取 ``category_membership`` 行数最多的
        日期，并列取较晚者——与文件版「降序遍历 + 严格大于」逐条等价。
        成员重建：``has_market=TRUE`` 带 ``sources.market.data``（至少含 ``market_cap``
        与 ``price_change_percentage_24h``，供 ``build_sectors`` 取数）；
        ``has_market=FALSE`` 不带 ``sources``（``build_sectors`` 自动 skip）。
        """
        try:
            if not is_valid_date(date):
                # 非法日期：文件版会「跳过窗口扫描 + 直接用 date 目录」；DB 无法把非日期
                # 字符串 cast 成 DATE，故直接委托文件版（结果同样为空），不走异常路径。
                print(f"[DuckDBRepository] 非法日期 {date!r}，跳过 by_category 7 日窗口扫描")
                return self._files.load_by_category_raw(date)

            picked = self._fetchall(
                """
                SELECT date FROM category_membership
                 WHERE date BETWEEN ?::DATE - INTERVAL 7 DAY AND ?::DATE
                 GROUP BY date ORDER BY COUNT(*) DESC, date DESC LIMIT 1
                """,
                [date, date],
            )
            resolved = _fmt_date(picked[0][0]) if picked else date

            rows = self._fetchall(
                """
                SELECT category_slug, member_key, coin_id, has_market, market_cap, chg24
                  FROM category_membership WHERE date = ?::DATE
                 ORDER BY category_slug, member_key
                """,
                [resolved],
            )
            if not rows:
                return self._files.load_by_category_raw(date)  # 目标日无行 → 请求级回退

            result: Dict[str, List[dict]] = {}
            for slug, _member_key, coin_id, has_market, market_cap, chg24 in rows:
                if has_market:
                    member: Dict[str, Any] = {
                        "coin_id": coin_id,
                        "sources": {
                            "market": {
                                "data": {
                                    "market_cap": market_cap,
                                    "price_change_percentage_24h": chg24,
                                }
                            }
                        },
                    }
                else:
                    member = {"coin_id": coin_id}
                result.setdefault(slug, []).append(member)
            return result
        except Exception as exc:  # noqa: BLE001
            print(f"[DuckDBRepository] load_by_category_raw 失败，回退文件：{exc}")
            return self._files.load_by_category_raw(date)

    def load_deep_raw(self, date: str) -> Dict[str, dict]:
        """查 ``deep_research`` 重建 ``{coin_id: 原始 dict}``（含**次日填充**）。

        与文件版等价：在 DB 的升序扫描日中取 ``date`` 的下一日先填充、请求当日覆盖。
        目标日不在 DB 扫描日中 → 请求级回退文件。
        """
        try:
            dates = self.list_scan_dates()
            if date not in dates:
                return self._files.load_deep_raw(date)
            idx = dates.index(date)
            next_day = dates[idx + 1] if idx + 1 < len(dates) else None
            deep: Dict[str, dict] = {}
            for d in ([next_day, date] if next_day else [date]):
                rows = self._fetchall(
                    "SELECT coin_id, payload_json FROM deep_research WHERE date = ?::DATE",
                    [d],
                )
                for cid, payload_json in rows:
                    if cid:
                        deep[cid] = _loads(payload_json)  # 当日覆盖次日
            return deep
        except Exception as exc:  # noqa: BLE001
            print(f"[DuckDBRepository] load_deep_raw 失败，回退文件：{exc}")
            return self._files.load_deep_raw(date)

    def find_coin_raw(self, date: str, coin_id: str) -> Optional[dict]:
        """查 ``deep_research`` 单条；未命中则按 by_category 成员兜底（同文件版）。"""
        try:
            rows = self._fetchall(
                "SELECT payload_json FROM deep_research WHERE date = ?::DATE AND coin_id = ?",
                [date, coin_id],
            )
            if rows and rows[0][0] is not None:
                return _loads(rows[0][0])
            # 兜底：与文件版同构地遍历 by_category 成员（含 7 日窗口解析）
            for members in self.load_by_category_raw(date).values():
                for m in members:
                    if m.get("coin_id") == coin_id:
                        return m
            return None
        except Exception as exc:  # noqa: BLE001
            print(f"[DuckDBRepository] find_coin_raw 失败，回退文件：{exc}")
            return self._files.find_coin_raw(date, coin_id)


# --------------------------------------------------------------------------
# 归一辅助
# --------------------------------------------------------------------------
def _fmt_date(value: Any) -> Optional[str]:
    """``date``/``datetime`` → ``YYYY-MM-DD`` 字符串；``None`` 原样返回。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "strftime"):  # datetime.date
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _fmt_ts(value: Any) -> Optional[str]:
    """``datetime`` → ISO 字符串（秒级）；字符串原样返回；``None`` 原样返回。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _loads(value: Any) -> Any:
    """把 JSON 文本解析为 Python 对象；``None`` 原样返回；解析失败返回 ``None``。"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None
    return value


# --------------------------------------------------------------------------
# 仓储工厂（模块级单例缓存）
# --------------------------------------------------------------------------
_repo: Optional[HistoryRepository] = None
_repo_lock = threading.Lock()


def get_repository() -> HistoryRepository:
    """返回当前配置下的仓储实现（进程内单例）。

    - ``CT_HISTORY_SOURCE=files``（默认）→ ``FileRepository``；
    - ``=duckdb`` 且 DB 可用 → ``DuckDBRepository``，否则回退 ``FileRepository``；
    - ``=auto`` 且 DB 可用 → ``DuckDBRepository``，否则 ``FileRepository``。
    """
    global _repo
    if _repo is not None:  # 快路径
        return _repo
    with _repo_lock:
        if _repo is not None:
            return _repo
        mode = (HISTORY_SOURCE or "files").strip().lower()
        if mode in ("duckdb", "auto") and duck.db_available():
            print(f"[repository] 使用 DuckDBRepository（mode={mode}）")
            _repo = DuckDBRepository(HISTORY_DB_PATH)
        else:
            if mode in ("duckdb", "auto"):
                print(f"[repository] 历史库不可用，回退 FileRepository（mode={mode}）")
            _repo = FileRepository()
        return _repo


def reset_repository() -> None:
    """清空仓储单例缓存（测试用：便于在同一进程内切换 ``CT_HISTORY_SOURCE``）。"""
    global _repo
    with _repo_lock:
        _repo = None
