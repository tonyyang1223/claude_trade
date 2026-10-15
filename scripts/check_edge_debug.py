import urllib.request
import json

try:
    with urllib.request.urlopen('http://localhost:9222/json', timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    print(f'找到 {len(targets)} 个调试目标：')
    for t in targets[:10]:
        title = t.get('title', '')[:50]
        url = t.get('url', '')[:60]
        print(f'  - {title} | {url}')
except Exception as e:
    print(f'错误: {e}')
