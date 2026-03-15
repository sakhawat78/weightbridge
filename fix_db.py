import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'weightbridge.db')
print("DB path:", db_path)
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)

if 'users' in tables:
    cur.execute("UPDATE users SET username='QAISER' WHERE username='admin'")
    print("Users updated:", cur.rowcount)
if 'transactions' in tables:
    cur.execute("UPDATE transactions SET operator='QAISER' WHERE operator='admin'")
    print("Transactions updated:", cur.rowcount)
if 'audit_log' in tables:
    cur.execute("UPDATE audit_log SET username='QAISER' WHERE username='admin'")
    print("Audit log updated:", cur.rowcount)
conn.commit()
conn.close()
