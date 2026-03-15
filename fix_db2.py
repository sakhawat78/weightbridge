import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'weightbridge.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    cur.execute("UPDATE operators SET username='QAISER' WHERE username='admin'")
    print("Operators updated:", cur.rowcount)
except Exception as e:
    print("Operators error:", e)

try:
    cur.execute("UPDATE transactions SET operator='QAISER' WHERE operator='admin'")
    print("Transactions updated:", cur.rowcount)
except Exception as e:
    print("Transactions error:", e)

try:
    cur.execute("UPDATE audit_log SET operator='QAISER' WHERE operator='admin'")
    print("Audit log updated:", cur.rowcount)
except Exception as e:
    print("Audit log error:", e)

conn.commit()
conn.close()
print("Success")
