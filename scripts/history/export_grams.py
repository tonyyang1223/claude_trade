"""生成 ``body_grams``：CJK 字符 bigram + 英文整词（英文不得切碎）。

设计依据：`docs/history-db/ARCHITECTURE.md` §0 验证1、§12「全文检索硬约定」。

背景（实测踩坑点）：
- DuckDB 的 simple 分词器**不切分 CJK**，把连续中文当作**单个 token**：
  整块连续中文可命中（`'以太坊'` 命中 `'以太坊 …'`），但**任意子串不可命中**
  （`'以太'` / `'坊'` 对整块 `'以太坊'` 不命中）。
- 因此在 ``content_archive.body_grams`` 里把 CJK 拆成**字符 bigram**（2 字最小粒度），
  中文子串（`'以太'` / `'治理'`）即可命中。
- **英文必须保留整词**：若把 `Solana` 也切成 `Sola/olan/lana`，则 `'Solana'` 搜不到，
  而 crypto 领域币名/协议名多为英文 → US-5 会大面积失效。
- ``body_grams`` 仅为 FTS 索引辅助列（与 ``body_text`` 组成**双列单索引**），
  **不返回前端**、查询侧也**不做任何 bigram 转换**。
"""
from __future__ import annotations

import re
import sys
from typing import List, Optional

# CJK / 假名 / 谚文 等「不以空格分词」的字符区间（取常用并集，够用即可）
_CJK_RANGES = (
    (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
    (0x3040, 0x30FF),    # Hiragana + Katakana
    (0xAC00, 0xD7AF),    # Hangul Syllables
)

_CJK_CHAR = re.compile("[" + "".join(chr(lo) + "-" + chr(hi) for lo, hi in _CJK_RANGES) + "]+")
# 英文/数字整词：以字母开头，后接字母/数字/下划线（保留整词，绝不切碎）
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*")

# CJK bigram 的最小粒度 = 2 字（单字不产生 bigram，但会原样保留该单字本身以便检索）
_BIGRAM_MIN = 2


def grams_for_cjk(run: str) -> List[str]:
    """把一段连续 CJK 文本转为字符 bigram 列表；单字段原样返回该单字。"""
    if not run:
        return []
    if len(run) < _BIGRAM_MIN:
        return [run]
    return [run[i : i + _BIGRAM_MIN] for i in range(len(run) - 1)]


def make_grams(text: Optional[str]) -> str:
    """把正文转成 FTS 辅助串：``CJK 字符 bigram + 英文整词``，空格分隔、去重。

    Args:
        text: 原始正文（可为 None / 空串）。

    Returns:
        空格分隔的 gram 串；``text`` 为空时返回空串。

    Examples:
        >>> make_grams("以太坊 ETF 审批通过")
        '以太 太坊 ETF 审批 批通 通过'
    """
    if not text:
        return ""

    out: List[str] = []
    seen: set = set()

    def _add(token: str) -> None:
        if token and token not in seen:
            seen.add(token)
            out.append(token)

    # 1) CJK：按「连续段」拆字符 bigram（避免跨标点产生无意义组合）
    for run in _CJK_CHAR.findall(text):
        for gram in grams_for_cjk(run):
            _add(gram)

    # 2) 英文：保留整词（大小写不敏感由索引侧 lower=1 负责，此处保留原样便于排查）
    for word in _WORD.findall(text):
        _add(word)

    return " ".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI：把文件内容（或 stdin）转成 grams 打印到 stdout，便于手工核对。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        with open(args[0], encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()
    print(make_grams(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
