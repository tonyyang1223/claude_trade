import sqlite3, json
conn = sqlite3.connect(r"C:\Users\P52S\DoubaoWork\chats\2026-09-25\new-chat\twitter_monitor\research.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, project, text FROM tweets ORDER BY project").fetchall()
data = []
for r in rows:
    data.append({"id": r["id"], "project": r["project"], "text": r["text"]})
print(json.dumps(data, ensure_ascii=False, indent=2))
conn.close()
