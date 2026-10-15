import json
d = json.load(open('data.json', 'r', encoding='utf-8'))
print(f'projects: {len(d["projects"])}')
print(f'tweets: {len(d["tweets"])}')
print(f'events: {len(d["events"])}')
print(f'updated: {d["last_updated"]}')
# 看看第100名左右的项目
for p in d['projects'][95:105]:
    print(f'  #{d["projects"].index(p)+1}: {p["symbol"]} ${p["price"]} mcap=${p["mcap"]:,.0f}')
