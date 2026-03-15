"""
db.py — Database layer for WeighBridge Pro
All tables, migrations, and helper queries live here.
"""

import sqlite3
import datetime
import random
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

DB_PATH  = BASE_DIR / "weightbridge.db"

MAX_WEIGHT_KG = 60_000.0
MIN_WEIGHT_KG = 100.0


# ─────────────────────────────── CONNECTION ──────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────── SCHEMA ──────────────────────────────────────
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # ── Operators ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS operators (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL DEFAULT 'operator',
            active   INTEGER NOT NULL DEFAULT 1,
            created  TEXT
        )
    """)

    # ── Vehicles ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            plate        TEXT UNIQUE NOT NULL,
            owner        TEXT,
            default_tare REAL DEFAULT 0,
            notes        TEXT,
            created      TEXT
        )
    """)

    # ── Materials ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT UNIQUE NOT NULL,
            unit_price REAL DEFAULT 0,
            unit       TEXT DEFAULT 'kg',
            notes      TEXT
        )
    """)

    # ── Transactions ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_seq   INTEGER,
            ticket_no    TEXT UNIQUE NOT NULL,
            vehicle_no   TEXT NOT NULL,
            driver_name  TEXT,
            material     TEXT,
            supplier     TEXT,
            party        TEXT,
            gross_wt     REAL DEFAULT 0,
            tare_wt      REAL DEFAULT 0,
            net_wt       REAL DEFAULT 0,
            unit         TEXT DEFAULT 'kg',
            rate         REAL DEFAULT 0,
            invoice_amt  REAL DEFAULT 0,
            weigh_in_time  TEXT,
            weigh_out_time TEXT,
            status       TEXT DEFAULT 'IN',
            operator     TEXT,
            remarks      TEXT,
            reweigh      INTEGER DEFAULT 0,
            reweigh_reason TEXT,
            entry_time   TEXT,
            exit_time    TEXT
        )
    """)

    # ── Audit Log ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       TEXT NOT NULL,
            operator TEXT NOT NULL,
            action   TEXT NOT NULL,
            detail   TEXT
        )
    """)

    # ── Settings ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # ── Ticket sequence counter ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS ticket_counter (
            id  INTEGER PRIMARY KEY CHECK (id = 1),
            seq INTEGER DEFAULT 0
        )
    """)
    c.execute("INSERT OR IGNORE INTO ticket_counter(id, seq) VALUES(1, 0)")

    # ── Seed defaults ──
    _seed_defaults(c)
    conn.commit()
    conn.close()


def _seed_defaults(c):
    now = now_str()

    # Default admin operator
    c.execute(
        "INSERT OR IGNORE INTO operators(username,password,role,active,created) VALUES(?,?,?,?,?)",
        ("QAISER", "admin123", "admin", 1, now)
    )
    c.execute(
        "INSERT OR IGNORE INTO operators(username,password,role,active,created) VALUES(?,?,?,?,?)",
        ("supervisor", "super123", "supervisor", 1, now)
    )
    c.execute(
        "INSERT OR IGNORE INTO operators(username,password,role,active,created) VALUES(?,?,?,?,?)",
        ("operator", "op123", "operator", 1, now)
    )

    # Default materials
    for name, price in [("Sand", 0), ("Gravel", 0), ("Coal", 0),
                        ("Wheat", 0), ("Scrap Metal", 0), ("Cement", 0)]:
        c.execute("INSERT OR IGNORE INTO materials(name,unit_price) VALUES(?,?)",
                  (name, price))

    # Default settings
    defaults = {
        "com_port":        "COM3",
        "baud_rate":       "9600",
        "parity":          "N",
        "data_bits":       "8",
        "stop_bits":       "1",
        "company_name":    "SAKHAWAT COMPUTERIZED SCALE ADA 59 PUL (MIANCHANNU)",
        "company_address": "123 Industrial Area",
        "company_phone":   "+1-000-000-0000",
        "units":           "kg",
        "min_weight":      "100",
        "max_weight":      "60000",
        "backup_days":     "1",
        "zero_offset":     "0",
        "logo_path":       "",
        "ticket_footer":   "",
        "scale_protocol":  "generic",
        "scale_timeout":   "3",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))


# ─────────────────────────────── HELPERS ─────────────────────────────────────
def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def kg_to_ton(kg: float) -> float:
    return round(float(kg) / 1000, 3)


def generate_ticket_no() -> str:
    """Sequential WB-00001 format ticket number."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE ticket_counter SET seq = seq + 1 WHERE id = 1")
    seq = c.execute("SELECT seq FROM ticket_counter WHERE id=1").fetchone()[0]
    conn.commit()
    conn.close()
    return f"WB-{seq:05d}"


def get_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()


def audit(operator: str, action: str, detail: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit_log(ts,operator,action,detail) VALUES(?,?,?,?)",
        (now_str(), operator, action, detail)
    )
    conn.commit()
    conn.close()


# ─────────────────────────── VEHICLE QUERIES ─────────────────────────────────
def get_all_plates() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT plate FROM vehicles ORDER BY plate").fetchall()
    conn.close()
    return [r["plate"] for r in rows]


def get_vehicle(plate: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM vehicles WHERE plate=?", (plate.upper(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_vehicle(plate, owner, default_tare, notes, vid=None):
    conn = get_conn()
    plate = plate.upper().strip()
    if vid:
        conn.execute(
            "UPDATE vehicles SET plate=?,owner=?,default_tare=?,notes=? WHERE id=?",
            (plate, owner, default_tare, notes, vid))
    else:
        conn.execute(
            "INSERT INTO vehicles(plate,owner,default_tare,notes,created) VALUES(?,?,?,?,?)",
            (plate, owner, default_tare, notes, now_str()))
    conn.commit()
    conn.close()


def delete_vehicle(vid: int):
    conn = get_conn()
    conn.execute("DELETE FROM vehicles WHERE id=?", (vid,))
    conn.commit()
    conn.close()


# ────────────────────────── MATERIAL QUERIES ─────────────────────────────────
def get_all_materials() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM materials ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_material_names() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT name FROM materials ORDER BY name").fetchall()
    conn.close()
    return [r["name"] for r in rows]


def save_material(name, unit_price, unit, notes, mid=None):
    conn = get_conn()
    if mid:
        conn.execute(
            "UPDATE materials SET name=?,unit_price=?,unit=?,notes=? WHERE id=?",
            (name, unit_price, unit, notes, mid))
    else:
        conn.execute(
            "INSERT INTO materials(name,unit_price,unit,notes) VALUES(?,?,?,?)",
            (name, unit_price, unit, notes))
    conn.commit()
    conn.close()


def delete_material(mid: int):
    conn = get_conn()
    conn.execute("DELETE FROM materials WHERE id=?", (mid,))
    conn.commit()
    conn.close()


# ──────────────────────── TRANSACTION QUERIES ─────────────────────────────────
def has_open_ticket(plate: str) -> bool:
    """Returns True if vehicle has an unfinished weigh-in."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM transactions WHERE vehicle_no=? AND status='IN'",
        (plate.upper(),)).fetchone()
    conn.close()
    return row is not None


def get_open_ticket(plate: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM transactions WHERE vehicle_no=? AND status='IN' ORDER BY id DESC LIMIT 1",
        (plate.upper(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_weigh_in(ticket_no, vehicle_no, driver_name, material,
                  supplier, party, tare_wt, operator, remarks=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO transactions
        (ticket_no, vehicle_no, driver_name, material, supplier, party,
         tare_wt, weigh_in_time, status, operator, remarks, entry_time)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ticket_no, vehicle_no.upper(), driver_name, material,
          supplier, party, tare_wt, now_str(), "IN", operator, remarks, now_str()))
    conn.commit()
    conn.close()


def save_weigh_out(ticket_no, weight_2, operator, remarks=""):
    conn = get_conn()
    row = conn.execute(
        "SELECT tare_wt, rate FROM transactions WHERE ticket_no=?",
        (ticket_no,)).fetchone()
    if not row:
        conn.close()
        return False
        
    weight_1 = row["tare_wt"]
    net = abs(weight_1 - weight_2)
    rate = row["rate"] or 0
    invoice = net * rate / 1000  # per ton
    conn.execute("""
        UPDATE transactions SET
            gross_wt=?, net_wt=?, invoice_amt=?,
            weigh_out_time=?, exit_time=?,
            status='OUT', remarks=?
        WHERE ticket_no=?
    """, (weight_2, net, invoice, now_str(), now_str(), remarks, ticket_no))
    conn.commit()
    conn.close()
    return True


def get_transactions(search="", status="ALL", from_dt=None, to_dt=None,
                     plate=None, material=None, limit=500):
    conn = get_conn()
    q = "SELECT * FROM transactions WHERE 1=1"
    params = []
    if status != "ALL":
        q += " AND status=?"; params.append(status)
    if plate:
        q += " AND vehicle_no LIKE ?"; params.append(f"%{plate.upper()}%")
    if material:
        q += " AND material LIKE ?"; params.append(f"%{material}%")
    if from_dt:
        q += " AND entry_time >= ?"; params.append(from_dt)
    if to_dt:
        q += " AND entry_time <= ?"; params.append(to_dt)
    if search:
        s = f"%{search}%"
        q += " AND (ticket_no LIKE ? OR vehicle_no LIKE ? OR material LIKE ? OR operator LIKE ?)"
        params += [s, s, s, s]
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_transaction(tid, **kwargs):
    conn = get_conn()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [tid]
    conn.execute(f"UPDATE transactions SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()


def delete_transaction(tid: int):
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE id=?", (tid,))
    conn.commit()
    conn.close()


# ──────────────────────── OPERATOR QUERIES ───────────────────────────────────
def login(username: str, password: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM operators WHERE username=? AND password=? AND active=1",
        (username, password)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_operators():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM operators ORDER BY username").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_operator(username, password, role, active=1, oid=None):
    conn = get_conn()
    now  = now_str()
    if oid:
        conn.execute(
            "UPDATE operators SET username=?,password=?,role=?,active=? WHERE id=?",
            (username, password, role, active, oid))
    else:
        conn.execute(
            "INSERT INTO operators(username,password,role,active,created) VALUES(?,?,?,?,?)",
            (username, password, role, active, now))
    conn.commit()
    conn.close()


def delete_operator(oid: int):
    conn = get_conn()
    conn.execute("DELETE FROM operators WHERE id=?", (oid,))
    conn.commit()
    conn.close()


# ──────────────────────── AUDIT QUERIES ──────────────────────────────────────
def get_audit_log(limit=1000):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
