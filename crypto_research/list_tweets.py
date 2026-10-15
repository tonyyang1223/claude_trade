import sqlite3
conn = sqlite3.connect(r"C:\Users\P52S\DoubaoWork\chats\2026-09-25\new-chat\twitter_monitor\research.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT project, author_handle, text FROM tweets ORDER BY project, likes DESC").fetchall()
for r in rows:
    print(f"[{r['project']}] @{r['author_handle']}: {r['text'][:200]}")
    print()
conn.close()
