import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'weightbridge.db')
print("Using DB:", db_path)

conn = sqlite3.connect(db_path)
conn.execute("UPDATE users SET username='QAISER' WHERE username='admin'")
conn.execute("UPDATE transactions SET operator='QAISER' WHERE operator='admin'")
conn.execute("UPDATE audit_log SET username='QAISER' WHERE username='admin'")
conn.commit()
conn.close()
print("Success")
