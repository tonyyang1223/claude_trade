"""拉取市值前300项目基本信息+行情，存入数据库"""
import urllib.request, json, sqlite3, time, ssl, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research.db")

def fetch_page(page, per_page=100):
    url = f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={per_page}&page={page}&price_change_percentage=1h,24h,7d,30d'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return json.loads(urllib.request.urlopen(req, timeout=30, context=ctx).read())

conn = sqlite3.connect(DB)
c = conn.cursor()
now = time.strftime('%Y-%m-%d %H:%M:%S')

all_coins = []
for page in range(1, 4):
    try:
        coins = fetch_page(page)
        all_coins.extend(coins)
        print(f'page {page}: {len(coins)} coins')
        time.sleep(1)
    except Exception as e:
        print(f'page {page} error: {e}')

new_projects = 0
price_count = 0
for coin in all_coins:
    sym = coin['symbol'].upper()
    name = coin['name']
    cgid = coin['id']
    
    c.execute('SELECT symbol FROM projects WHERE symbol=?', (sym,))
    if not c.fetchone():
        c.execute('''INSERT INTO projects (symbol, name, coin_gecko_id, added_at, last_updated)
                     VALUES (?,?,?,?,?)''', (sym, name, cgid, now, now))
        new_projects += 1
    else:
        c.execute('UPDATE projects SET last_updated=?, name=? WHERE symbol=?', (now, name, sym))
    
    c.execute('''INSERT INTO price_snapshots
        (project, price, change_1h, change_24h, change_7d, change_30d,
         market_cap, volume_24h, ath, ath_date, atl, circulating_supply,
         total_supply, max_supply, fdv, snapshot_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (sym, coin['current_price'],
         coin.get('price_change_percentage_1h_in_currency'),
         coin.get('price_change_percentage_24h'),
         coin.get('price_change_percentage_7d_in_currency'),
         coin.get('price_change_percentage_30d_in_currency'),
         coin['market_cap'], coin['total_volume'],
         coin.get('ath'), coin.get('ath_date'), coin.get('atl'),
         coin.get('circulating_supply'), coin.get('total_supply'),
         coin.get('max_supply'), coin.get('fully_diluted_valuation'), now))
    price_count += 1

conn.commit()
print(f'\n总共拉取 {len(all_coins)} 个项目')
print(f'新增项目 {new_projects} 个，行情快照 {price_count} 条')

c.execute('SELECT COUNT(*) FROM projects')
total_projects = c.fetchone()[0]
print(f'数据库中现有项目总数: {total_projects}')

print('\nTop 10:')
for coin in all_coins[:10]:
    sym = coin['symbol'].upper()
    price = coin['current_price']
    ch24 = coin.get('price_change_percentage_24h') or 0
    mcap = coin['market_cap'] or 0
    print(f'  {sym}: ${price} ({ch24:+.2f}%) MCap=${mcap:,.0f}')

conn.close()
