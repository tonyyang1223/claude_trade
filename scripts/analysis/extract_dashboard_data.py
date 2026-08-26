# -*- coding: utf-8 -*-
"""extract_dashboard_data.py — 抽取看板数据为独立 JSON 文件, 供各页面引用"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from build_dashboard import collect_dashboard_data, ROOT

OUT_DIR = os.path.join(ROOT, "reports", "dashboard")
os.makedirs(OUT_DIR, exist_ok=True)


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    if not date_str:
        scan_dir = os.path.join(ROOT, "data", "reports", "daily_scan")
        days = sorted(d for d in os.listdir(scan_dir)
                      if os.path.isdir(os.path.join(scan_dir, d)))
        date_str = days[-1]

    data = collect_dashboard_data(date_str)

    # 按 Tab 拆分成独立 JSON
    parts = {
        "meta.json": data["meta"],
        "kpi.json": data["kpi"],
        "market.json": {
            "dist": data["dist"],
            "gainers": data["gainers"],
            "losers": data["losers"],
            "topMcap": data["topMcap"],
            "topVol": data["topVol"],
            "scatter": data["scatter"],
            "coinCnt": data["kpi"]["coinCnt"],
        },
        "sectors.json": {
            "cats": data["cats"],
            "catTop": data["catTop"],
            "catDay": data["meta"]["catDay"],
        },
        "deep.json": {
            "deep": data["deep"],
            "date": data["meta"]["date"],
            "prevDay": data["meta"]["prevDay"],
        },
        "funds.json": {
            "stablecoins": data["stablecoins"],
            "ethTvl": data["ethTvl"],
            "github": data["github"],
            "dayCmp": data["dayCmp"],
            "queueLen": data["meta"]["queueLen"],
            "lightTotal": data["meta"]["lightTotal"],
            "deepTotal": data["meta"]["deepTotal"],
        },
    }
    for name, obj in parts.items():
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
    # 合并的索引文件 (供首页用)
    with open(os.path.join(OUT_DIR, "index_data.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": data["meta"], "kpi": data["kpi"]}, f, ensure_ascii=False)

    print(f"数据已抽取到 {OUT_DIR}/ ({len(parts)+1} 个文件)")
    print(f"  日期: {date_str} | 币种: {data['kpi']['coinCnt']} | 深度研究: {data['kpi']['deepStudied']} | 板块: {len(data['cats'])}")


if __name__ == "__main__":
    main()
