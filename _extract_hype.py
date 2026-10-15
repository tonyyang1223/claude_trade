import json
d = json.load(open(r'reports\_raw_hype_data_20261009_041035.json', encoding='utf-8'))
for sym, c in d['coins'].items():
    if 'error' in c:
        print(sym, 'ERROR', c['error']); continue
    print(f"{sym}: price={c['current_price_usd']}, mc={c['market_cap_usd']}, fdv={c['fully_diluted_valuation_usd']}, circ={c['circulating_supply']}, total={c['total_supply']}, max={c['max_supply']}, ath={c['ath_usd']} @ {c['ath_date']}, vol24h={c['total_volume_usd']}")
print('--- TVL ---')
for sym, t in d.get('tvl', {}).items():
    if 'error' in t:
        print(sym, 'ERR', t['error']); continue
    tvl = t.get('tvl')
    if isinstance(tvl, list):
        tvl = tvl[-1] if tvl else None
    print(f"{sym}: tvl={tvl}, chain={t.get('chain')}, cat={t.get('category')}, listedAt={t.get('listedAt')}")
