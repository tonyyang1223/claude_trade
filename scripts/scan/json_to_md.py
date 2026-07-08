#!/usr/bin/env python3
"""Convert JSON research reports to Markdown documents.

Usage:
  python3 scripts/scan/json_to_md.py                     # Convert today's reports
  python3 scripts/scan/json_to_md.py --date 2026-06-29   # Convert specific date
  python3 scripts/scan/json_to_md.py --all               # Convert all dates
  python3 scripts/scan/json_to_md.py --push              # Convert and git push
"""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

project_root = Path(__file__).parent.parent.parent


# ── Format helpers ──

def format_currency(value: Optional[float]) -> str:
    """Format large numbers as currency ($1.2T, $3.5B, $2.1M, $150K)."""
    if value is None:
        return "N/A"
    if value >= 1e12:
        return f"${value/1e12:.2f}T"
    if value >= 1e9:
        return f"${value/1e9:.2f}B"
    if value >= 1e6:
        return f"${value/1e6:.2f}M"
    if value >= 1e3:
        return f"${value/1e3:.1f}K"
    return f"${value:.2f}"


def format_number(value: Optional[float], unit: str = "") -> str:
    """Format large numbers with units (1.2T, 3.5B, 2.1M)."""
    if value is None:
        return "N/A"
    if value >= 1e12:
        return f"{value/1e12:.2f}T{unit}"
    if value >= 1e9:
        return f"{value/1e9:.2f}B{unit}"
    if value >= 1e6:
        return f"{value/1e6:.2f}M{unit}"
    if value >= 1e3:
        return f"{value/1e3:.1f}K{unit}"
    return f"{value:.2f}{unit}"


def format_pct(value: Optional[float]) -> str:
    """Format percentage with +/- sign."""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def format_supply(value: Optional[float], symbol: str = "") -> str:
    """Format supply numbers."""
    if value is None:
        return "N/A"
    return f"{format_number(value)} {symbol}"


def get_source_data(report: Dict, source_key: str) -> Optional[Dict]:
    """Extract data from a source, return None if error or missing."""
    sources = report.get("sources", {})
    src = sources.get(source_key, {})
    if src.get("status") == "ok":
        return src.get("data")
    return None


# ── Coin to Markdown ──

def coin_to_md(coin_id: str, report: Dict) -> str:
    """Convert a single coin's deep research JSON to Markdown."""
    symbol = report.get("symbol", "").upper()
    name = report.get("name", coin_id)
    rank = report.get("rank")
    category = report.get("category_slug", "unclassified")
    research_time = report.get("research_time", "")

    # Format header
    rank_str = f"#{rank}" if rank else "N/A"
    time_str = research_time[:16] if research_time else "N/A"

    lines = [
        f"# {name} ({symbol})",
        "",
        f"> 排名 {rank_str} | {category} | 更新于 {time_str}",
        "",
    ]

    # Market data
    market = get_source_data(report, "market")
    if market:
        lines.extend([
            "## 市场数据",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
        ])
        price = market.get("current_price")
        mcap = market.get("market_cap")
        vol = market.get("total_volume")
        chg_24h = market.get("price_change_percentage_24h")
        circ = market.get("circulating_supply")
        max_sup = market.get("max_supply")

        lines.append(f"| 价格 | {format_currency(price)} |")
        lines.append(f"| 市值 | {format_currency(mcap)} |")
        lines.append(f"| 24h交易量 | {format_currency(vol)} |")
        lines.append(f"| 24h涨跌 | {format_pct(chg_24h)} |")
        lines.append(f"| 流通量 | {format_supply(circ, symbol)} |")
        lines.append(f"| 最大供应 | {format_supply(max_sup, symbol)} |")
        lines.append("")

    # Funding rate & Open interest
    funding = get_source_data(report, "funding_rate")
    oi = get_source_data(report, "open_interest")

    if funding or oi:
        lines.extend([
            "## 资金费率 & 持仓",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
        ])
        if funding:
            fr = funding.get("avg_funding_rate")
            lines.append(f"| 平均资金费率 | {format_pct(fr * 100) if fr else 'N/A'} |")
        if oi:
            oi_val = oi.get("total_open_interest")
            oi_chg = oi.get("oi_change_24h")
            lines.append(f"| 持仓量 | {format_currency(oi_val)} |")
            lines.append(f"| 持仓24h变化 | {format_pct(oi_chg)} |")
        lines.append("")

    # Stablecoin flows (only relevant for stablecoins)
    stable = get_source_data(report, "stablecoin_flows")
    if stable and category == "stablecoin":
        flows = stable.get("net_flows_24h")
        lines.extend([
            "## 稳定币流向",
            "",
            f"24h净流向: {format_currency(flows)}",
            "",
        ])

    # Twitter
    twitter = get_source_data(report, "twitter")
    if twitter:
        lines.extend([
            "## 社交数据",
            "",
            "### Twitter",
            "",
        ])
        username = twitter.get("username", "")
        followers = twitter.get("followers")
        tweets = twitter.get("tweets_count")
        if username:
            lines.append(f"- 用户: @{username}")
        if followers:
            lines.append(f"- 关注者: {format_number(followers)}")
        if tweets:
            lines.append(f"- 推文数: {tweets}")
        lines.append("")

    # Crypto news
    news = get_source_data(report, "crypto_news")
    if news:
        items = news if isinstance(news, list) else news.get("data", [])
        if items:
            lines.extend([
                "### 社区新闻",
                "",
            ])
            for i, item in enumerate(items[:5], 1):
                title = item.get("title", "") if isinstance(item, dict) else str(item)
                src = item.get("source", "") if isinstance(item, dict) else ""
                lines.append(f"{i}. **{title}** - {src}")
            lines.append("")

    # GitHub
    github = get_source_data(report, "github")
    if github:
        lines.extend([
            "## GitHub",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
        ])
        stars = github.get("stargazers_count")
        forks = github.get("forks_count")
        lang = github.get("language", "")
        license_name = github.get("license", {}).get("spdx_id", "") if github.get("license") else ""

        lines.append(f"| Stars | {format_number(stars)} |")
        lines.append(f"| Forks | {format_number(forks)} |")
        lines.append(f"| 语言 | {lang} |")
        lines.append(f"| License | {license_name} |")
        lines.append("")

    # Sentiment
    sentiment = get_source_data(report, "sentiment")
    if sentiment:
        lines.extend([
            "## 情绪指标",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
        ])
        fg = sentiment.get("fear_greed", {})
        fg_val = fg.get("value")
        fg_class = fg.get("classification", "")
        combined = sentiment.get("combined_score")
        rec = sentiment.get("recommendation", "")

        if fg_val:
            lines.append(f"| 恐惧贪婪 | {fg_val} ({fg_class}) |")
        if combined:
            lines.append(f"| 综合评分 | {combined}/100 |")
        if rec:
            lines.append(f"| 建议 | {rec} |")
        lines.append("")

    # Social stats (from socialtickers.com)
    social_stats = get_source_data(report, "social_stats")
    if social_stats:
        overall = social_stats.get("overall", {})
        reddit_stats = social_stats.get("reddit", {})
        trend = social_stats.get("trend", {})

        lines.extend([
            "## 社交活跃度",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
        ])
        mentions = overall.get("mentions", 0)
        upvotes = overall.get("upvotes", 0)
        signal = overall.get("signal", 50)
        intensity = overall.get("intensity", 0)

        lines.append(f"| 提及量 | {mentions} |")
        lines.append(f"| 点赞数 | {upvotes} |")
        lines.append(f"| 情绪信号 | {signal}/100 |")
        if intensity:
            lines.append(f"| 活跃强度 | {intensity:.2f} |")

        # Reddit stats
        if reddit_stats:
            subscribers = reddit_stats.get("subscribers", 0)
            active = reddit_stats.get("active_users", 0)
            lines.append(f"| Reddit订阅 | {format_number(subscribers)} |")
            lines.append(f"| Reddit活跃 | {active} |")

        # Trend
        if trend.get("direction"):
            dir_emoji = "📈" if trend.get("direction") == "up" else "📉"
            lines.append(f"| 趋势 | {dir_emoji} {trend.get('direction')} |")

        lines.append("")

    # Footer
    lines.extend([
        "---",
        f"*数据来源: CoinGecko, Binance, DefiLlama, socialtickers, Twitter, GitHub, SentimentAPI*",
        f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ])

    return "\n".join(lines)


# ── Daily Summary Markdown ──

def daily_summary_md(date: str, summary: Dict, light_data: List[Dict]) -> str:
    """Generate daily summary Markdown."""
    scan_time = summary.get("scan_time", "")[:16]
    total = summary.get("total_coins", 0)
    deep = summary.get("deep_researched", 0)
    light = summary.get("light_researched", 0)
    categories = summary.get("categories", {})
    market = summary.get("market_stats", {})

    lines = [
        f"# 每日扫描报告 - {date}",
        "",
        "## 概览",
        "",
        f"- 扫描时间: {scan_time}",
        f"- 总币数: {total}",
        f"- 深度研究: {deep} 个币",
        f"- 轻量数据: {light} 个币",
        "",
        "## 分类统计",
        "",
        "| 分类 | 数量 |",
        "|------|------|",
    ]

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        lines.append(f"| {cat} | {count} |")
    lines.append("")

    # Market stats
    lines.extend([
        "## 市场统计",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
    ])
    mcap = market.get("total_market_cap")
    avg_chg = market.get("avg_change_24h_pct")
    fg = market.get("fear_greed_index")

    lines.append(f"| 总市值 | {format_currency(mcap)} |")
    lines.append(f"| 平均24h涨跌 | {format_pct(avg_chg)} |")
    lines.append(f"| 恐惧贪婪指数 | {fg or 'N/A'} |")
    lines.append("")

    # Top 10 from light data
    lines.extend([
        "## Top 10 涨跌榜",
        "",
        "| 排名 | 币种 | 价格 | 24h涨跌 |",
        "|------|------|------|---------|",
    ])

    for coin in light_data[:10]:
        rank = coin.get("rank", "?")
        name = coin.get("name", "")
        sym = coin.get("symbol", "")
        price = coin.get("price_usd")
        chg = coin.get("change_24h_pct")
        lines.append(f"| {rank} | {name} ({sym}) | {format_currency(price)} | {format_pct(chg)} |")
    lines.append("")

    # Footer
    lines.extend([
        "---",
        f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ])

    return "\n".join(lines)


# ── Main conversion ──

def convert_date(date_str: str) -> int:
    """Convert all JSON reports for a given date to Markdown."""
    base_dir = project_root / "data" / "reports" / "daily_scan" / date_str

    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return 0

    # Create output directory
    md_dir = base_dir / "md_reports"
    md_dir.mkdir(parents=True, exist_ok=True)

    count = 0

    # Convert deep research JSONs
    detailed_dir = base_dir / "top_50_detailed"
    if detailed_dir.exists():
        for json_file in detailed_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                coin_id = json_file.stem
                md_content = coin_to_md(coin_id, data)
                md_file = md_dir / f"{coin_id}.md"
                md_file.write_text(md_content, encoding="utf-8")
                count += 1
                print(f"  Converted: {coin_id}.md")
            except Exception as e:
                print(f"  Error converting {json_file}: {e}")

    # Generate daily summary
    summary_file = base_dir / "summary.json"
    light_file = base_dir / "top_800_light" / "all_coins.json"

    if summary_file.exists() and light_file.exists():
        try:
            summary = json.loads(summary_file.read_text(encoding="utf-8"))
            light_data = json.loads(light_file.read_text(encoding="utf-8"))
            summary_md = daily_summary_md(date_str, summary, light_data)
            summary_md_file = md_dir / "daily_summary.md"
            summary_md_file.write_text(summary_md, encoding="utf-8")
            print(f"  Generated: daily_summary.md")
        except Exception as e:
            print(f"  Error generating summary: {e}")

    return count


def convert_all_dates() -> int:
    """Convert all dates in the daily_scan directory."""
    base_dir = project_root / "data" / "reports" / "daily_scan"
    total = 0

    for date_dir in sorted(base_dir.iterdir()):
        if date_dir.is_dir() and date_dir.name.startswith("2026-"):
            print(f"\nConverting {date_dir.name}...")
            total += convert_date(date_dir.name)

    return total


def git_push():
    """Git add, commit, and push."""
    # Add md_reports directories
    subprocess.run(["git", "add", "data/reports/daily_scan/*/md_reports/"], check=False)
    subprocess.run(["git", "add", "data/reports/daily_scan/scan_state.json"], check=False)
    subprocess.run(["git", "add", "data/reports/daily_scan/daemon.log"], check=False)

    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)

    if not result.stdout.strip():
        print("No changes to commit")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Use -a to stage all tracked files that have been modified
    subprocess.run([
        "git", "commit", "-a", "-m",
        f"docs: 更新 Markdown 研究报告 ({now})\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
    ], check=True)

    subprocess.run(["git", "push"], check=True)
    print("Pushed to remote")


def main():
    parser = argparse.ArgumentParser(description="Convert JSON reports to Markdown")
    parser.add_argument("--date", type=str, default=None, help="Date to convert (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="Convert all dates")
    parser.add_argument("--push", action="store_true", help="Git commit and push after conversion")
    args = parser.parse_args()

    if args.all:
        total = convert_all_dates()
        print(f"\nTotal files converted: {total}")
    elif args.date:
        count = convert_date(args.date)
        print(f"\nConverted {count} files for {args.date}")
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        count = convert_date(today)
        print(f"\nConverted {count} files for {today}")

    if args.push:
        git_push()


if __name__ == "__main__":
    main()