import urllib.request
import json

# Reddit 公开 JSON API，不需要登录
url = "https://www.reddit.com/r/bittensor_/top/.json?t=month&limit=15"

req = urllib.request.Request(url, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    
    posts = data.get("data", {}).get("children", [])
    print(f"成功获取 {len(posts)} 个热门帖子：\n")
    
    for i, post in enumerate(posts, 1):
        d = post.get("data", {})
        title = d.get("title", "")[:80]
        score = d.get("score", 0)
        num_comments = d.get("num_comments", 0)
        author = d.get("author", "")
        created = d.get("created_utc", 0)
        selftext = d.get("selftext", "")[:200]
        
        print(f"[{i}] {title}")
        print(f"    作者: u/{author} | 赞: {score} | 评论: {num_comments}")
        if selftext:
            print(f"    摘要: {selftext[:150]}...")
        print()
        
except Exception as e:
    print(f"错误: {e}")
