"""
生成项目分析报告
用法: python report.py ONDO
"""
import sys
from db import *

def report(symbol):
    data = get_project_data(symbol.upper())
    p = data['project']

    print(f"\n{'='*70}")
    print(f"  {p.get('name',symbol)} ({symbol.upper()}) 深度研究报告")
    print(f"{'='*70}")

    if not p:
        print("  项目未找到，请先运行 research.py")
        return

    # 基本信息
    print(f"\n【基本信息】")
    print(f"  类别: {p.get('category','N/A')}")
    print(f"  官网: {p.get('website','N/A')}")
    print(f"  Twitter: {p.get('twitter','N/A')}")
    print(f"  GitHub: {p.get('github','N/A')}")
    desc = p.get('description','')
    if desc:
        print(f"  简介: {desc[:200]}...")

    # 最新行情
    if data['prices']:
        latest = data['prices'][0]
        print(f"\n【最新行情】")
        print(f"  价格: ${latest['price']}")
        print(f"  24h: {latest.get('change_24h',0):.2f}%  |  7d: {latest.get('change_7d',0):.2f}%  |  30d: {latest.get('change_30d',0):.2f}%")
        print(f"  市值: ${latest.get('market_cap',0):,.0f}")
        print(f"  24h量: ${latest.get('volume_24h',0):,.0f}")
        print(f"  ATH: ${latest.get('ath',0)}")
        if latest.get('ath') and latest['ath'] > 0:
            print(f"  距ATH: {(latest['price']/latest['ath']-1)*100:.1f}%")
        print(f"  FDV: ${latest.get('fdv',0):,.0f}")
        print(f"  流通率: {(latest.get('circulating_supply',0)/latest.get('total_supply',1)*100):.1f}%")

    # 事件时间线
    if data['events']:
        print(f"\n【关键事件时间线】({len(data['events'])}个)")
        for e in data['events']:
            print(f"  [{e['event_date']}] {e['event_type']}: {e['title']}")
            print(f"    {e['description'][:150]}")
            if e.get('impact'):
                print(f"    影响: {e['impact']}")

    # 高互动推文
    if data['tweets']:
        print(f"\n【高互动推文 TOP 5】")
        for t in data['tweets'][:5]:
            print(f"  @{t['author_handle']} ({t.get('likes',0)} likes):")
            print(f"    {t['text'][:150]}")

    # 竞品
    if data['competitors']:
        print(f"\n【竞争对手】")
        for c in data['competitors']:
            print(f"  {c['competitor_symbol']} ({c.get('competitor_name','')}): {c.get('advantage','')}")

    # 六维评分
    if data['scores']:
        print(f"\n【六维评分】")
        total = 0
        for s in data['scores']:
            weighted = s['score'] * s['weight']
            total += weighted
            print(f"  {s['dimension']}: {s['score']}/5 (权重{s['weight']*100:.0f}%) - {s.get('notes','')}")
        print(f"  ────────────────────────")
        print(f"  综合得分: {total:.2f}/5.0")

    # AI报告
    if data['reports']:
        r = data['reports'][0]
        print(f"\n【AI分析】")
        print(f"  评级: {r.get('rating','N/A')}")
        print(f"  目标价: {r.get('target_price','N/A')}")
        print(f"  看多: {r.get('bull_case','')[:200]}")
        print(f"  看空: {r.get('bear_case','')[:200]}")
        print(f"  催化剂: {r.get('catalysts','')[:200]}")
        print(f"  风险: {r.get('risks','')[:200]}")

    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python report.py <SYMBOL>")
        sys.exit(1)
    report(sys.argv[1])
