import sqlite3
conn = sqlite3.connect('research.db')
c = conn.cursor()
for table in ['price_snapshots', 'projects', 'tweets']:
    c.execute(f"PRAGMA table_info({table})")
    print(f"=== {table} ===")
    for col in c.fetchall():
        print(col)
conn.close()
