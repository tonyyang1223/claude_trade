import urllib.request, json, sqlite3, time

url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&price_change_percentage=1h,24h,7d,30d'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
data = json.loads(urllib.request.urlopen(req, timeout=30).read())

conn = sqlite3.connect('research.db')
c = conn.cursor()

now = time.strftime('%Y-%m-%d %H:%M:%S')
count = 0
for coin in data:
    sym = coin['symbol'].upper()
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
    count += 1

conn.commit()
print(f'更新了{count}个项目行情，时间: {now}')
for coin in data[:15]:
    sym = coin['symbol'].upper()
    price = coin['current_price']
    ch24 = coin.get('price_change_percentage_24h') or 0
    ch7d = coin.get('price_change_percentage_7d_in_currency') or 0
    mcap = coin['market_cap'] or 0
    print(f'{sym}: ${price} ({ch24:.2f}% 24h, {ch7d:.2f}% 7d) MCap=${mcap:,.0f}')
conn.close()
