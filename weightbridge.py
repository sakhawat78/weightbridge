"""
╔══════════════════════════════════════════════════════════════════════╗
║             WEIGHTBRIDGE MANAGEMENT SYSTEM                          ║
║             Built with Python + Tkinter + SQLite                    ║
╚══════════════════════════════════════════════════════════════════════╝

Features:
  • Vehicle entry & exit with gross/tare/net weight calculation
  • Live weighing display with animated scale indicator
  • Transaction history with search & filter
  • CSV & PDF report export
  • Dark/Light theme toggle
  • SQLite database (auto-created)
  • Operator login system
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import csv
import random
import datetime
from pathlib import Path

# ─────────────────────────────── CONSTANTS ───────────────────────────────────
DB_PATH = Path(__file__).parent / "weightbridge.db"
APP_TITLE = "WeighBridge Pro"
VERSION = "v1.0"

# ─────────────────── COLOUR PALETTES (Dark / Light) ──────────────────────────
DARK = {
    "bg": "#0d1117",
    "surface": "#161b22",
    "card": "#1c2333",
    "border": "#30363d",
    "accent": "#58a6ff",
    "accent2": "#3fb950",
    "danger": "#f85149",
    "warning": "#d29922",
    "text": "#e6edf3",
    "text_muted": "#8b949e",
    "text_dim": "#484f58",
    "entry_bg": "#0d1117",
    "btn_bg": "#21262d",
    "btn_hover": "#30363d",
    "scale_bg": "#1c2333",
    "highlight": "#1f6feb",
}

LIGHT = {
    "bg": "#f5f7fa",
    "surface": "#ffffff",
    "card": "#f0f4f8",
    "border": "#d0d7de",
    "accent": "#0969da",
    "accent2": "#1a7f37",
    "danger": "#cf222e",
    "warning": "#9a6700",
    "text": "#1f2328",
    "text_muted": "#656d76",
    "text_dim": "#bbc0c7",
    "entry_bg": "#ffffff",
    "btn_bg": "#f3f4f6",
    "btn_hover": "#e7eaed",
    "scale_bg": "#f0f4f8",
    "highlight": "#0969da",
}

# ─────────────────────────────── DATABASE ────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_no   TEXT UNIQUE NOT NULL,
            vehicle_no  TEXT NOT NULL,
            driver_name TEXT,
            material    TEXT,
            supplier    TEXT,
            party       TEXT,
            gross_wt    REAL DEFAULT 0,
            tare_wt     REAL DEFAULT 0,
            net_wt      REAL DEFAULT 0,
            unit        TEXT DEFAULT 'kg',
            entry_time  TEXT,
            exit_time   TEXT,
            status      TEXT DEFAULT 'IN',
            operator    TEXT,
            remarks     TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS operators (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT DEFAULT 'operator'
        )
    """)
    # seed default admin
    c.execute("INSERT OR IGNORE INTO operators(username,password,role) VALUES(?,?,?)",
              ("admin", "admin123", "admin"))
    conn.commit()
    conn.close()


def get_conn():
    return sqlite3.connect(DB_PATH)


def generate_ticket():
    now = datetime.datetime.now()
    return f"WB{now.strftime('%Y%m%d%H%M%S')}{random.randint(10,99)}"


# ─────────────────────────────── HELPERS ─────────────────────────────────────
def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def kg_to_ton(kg):
    return round(kg / 1000, 3)


# ══════════════════════════════════════════════════════════════════════════════
#                              LOGIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} — Login")
        self.resizable(False, False)
        self.configure(bg=DARK["bg"])
        self._center(420, 560)
        self._build_ui()

    def _center(self, w, h):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        C = DARK
        # Header
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill="x", padx=0, pady=(40, 0))

        tk.Label(header, text="⚖", font=("Segoe UI", 52), bg=C["bg"],
                 fg=C["accent"]).pack()
        tk.Label(header, text=APP_TITLE, font=("Segoe UI", 22, "bold"),
                 bg=C["bg"], fg=C["text"]).pack()
        tk.Label(header, text="Weighbridge Management System",
                 font=("Segoe UI", 10), bg=C["bg"], fg=C["text_muted"]).pack(pady=(2, 0))

        # Card
        card = tk.Frame(self, bg=C["card"], bd=0, relief="flat",
                        highlightbackground=C["border"], highlightthickness=1)
        card.pack(fill="x", padx=40, pady=30)

        tk.Label(card, text="Sign In", font=("Segoe UI", 14, "bold"),
                 bg=C["card"], fg=C["text"]).pack(pady=(24, 16))

        # ── Username ──
        tk.Label(card, text="Username", font=("Segoe UI", 9),
                 bg=C["card"], fg=C["text_muted"]).pack(anchor="w", padx=24)
        self.user_var = tk.StringVar(value="admin")
        user_entry = tk.Entry(card, textvariable=self.user_var,
                              font=("Segoe UI", 11), bg=C["entry_bg"],
                              fg=C["text"], insertbackground=C["text"],
                              relief="flat", bd=0,
                              highlightbackground=C["border"],
                              highlightthickness=1)
        user_entry.pack(fill="x", padx=24, ipady=8, pady=(4, 14))

        # ── Password ──
        tk.Label(card, text="Password", font=("Segoe UI", 9),
                 bg=C["card"], fg=C["text_muted"]).pack(anchor="w", padx=24)
        self.pass_var = tk.StringVar(value="admin123")
        pass_entry = tk.Entry(card, textvariable=self.pass_var, show="●",
                              font=("Segoe UI", 11), bg=C["entry_bg"],
                              fg=C["text"], insertbackground=C["text"],
                              relief="flat", bd=0,
                              highlightbackground=C["border"],
                              highlightthickness=1)
        pass_entry.pack(fill="x", padx=24, ipady=8, pady=(4, 20))

        self.msg_var = tk.StringVar()
        tk.Label(card, textvariable=self.msg_var, font=("Segoe UI", 9),
                 bg=C["card"], fg=C["danger"]).pack()

        # ── Login button ──
        btn = tk.Button(card, text="  LOGIN  ", font=("Segoe UI", 11, "bold"),
                        bg=C["accent"], fg="#ffffff", activebackground="#79c0ff",
                        activeforeground="#ffffff", relief="flat", bd=0,
                        cursor="hand2", command=self._login)
        btn.pack(fill="x", padx=24, ipady=10, pady=(8, 24))

        tk.Label(self, text=f"Default: admin / admin123  •  {VERSION}",
                 font=("Segoe UI", 8), bg=C["bg"], fg=C["text_dim"]).pack(pady=(0, 10))

        self.bind("<Return>", lambda e: self._login())

    def _login(self):
        u = self.user_var.get().strip()
        p = self.pass_var.get().strip()
        conn = get_conn()
        row = conn.execute(
            "SELECT username, role FROM operators WHERE username=? AND password=?", (u, p)
        ).fetchone()
        conn.close()
        if row:
            self.destroy()
            app = WeighbridgeApp(operator=row[0], role=row[1])
            app.mainloop()
        else:
            self.msg_var.set("❌  Invalid username or password")


# ══════════════════════════════════════════════════════════════════════════════
#                         MAIN APPLICATION WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class WeighbridgeApp(tk.Tk):
    def __init__(self, operator="admin", role="admin"):
        super().__init__()
        self.operator = operator
        self.role = role
        self.theme = "dark"
        self.C = DARK.copy()

        self.title(f"{APP_TITLE}  —  {operator}  ({role})")
        self.state("zoomed")          # maximise on Windows
        self.configure(bg=self.C["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._simulated_weight = tk.DoubleVar(value=0.0)
        self._target_weight = 0.0
        self._anim_running = False

        self._build_ui()
        self._animate_scale()
        self._refresh_table()

    # ─────────────────────────── LAYOUT ──────────────────────────────────────
    def _build_ui(self):
        C = self.C
        # ── Topbar ──
        self._build_topbar()
        # ── Main 3-pane layout ──
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=5)
        main.rowconfigure(0, weight=1)

        left = tk.Frame(main, bg=C["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right = tk.Frame(main, bg=C["bg"])
        right.grid(row=0, column=1, sticky="nsew")

        self._build_scale_card(left)
        self._build_form_card(left)
        self._build_history_panel(right)

    def _build_topbar(self):
        C = self.C
        bar = tk.Frame(self, bg=C["surface"],
                       highlightbackground=C["border"], highlightthickness=1)
        bar.pack(fill="x")

        inner = tk.Frame(bar, bg=C["surface"])
        inner.pack(fill="x", padx=20, pady=10)

        # Left logos
        tk.Label(inner, text="⚖  WeighBridge Pro", font=("Segoe UI", 13, "bold"),
                 bg=C["surface"], fg=C["accent"]).pack(side="left")

        # Right buttons
        right_frame = tk.Frame(inner, bg=C["surface"])
        right_frame.pack(side="right")

        self._theme_btn = tk.Button(right_frame, text="☀ Light",
                                    font=("Segoe UI", 9), bg=C["btn_bg"],
                                    fg=C["text"], relief="flat", bd=0,
                                    cursor="hand2", command=self._toggle_theme,
                                    padx=10)
        self._theme_btn.pack(side="left", padx=(0, 8))

        tk.Button(right_frame, text="📤 Export CSV",
                  font=("Segoe UI", 9), bg=C["btn_bg"], fg=C["text"],
                  relief="flat", bd=0, cursor="hand2",
                  command=self._export_csv, padx=10).pack(side="left", padx=(0, 8))

        tk.Label(right_frame,
                 text=f"👤 {self.operator.upper()}  [{self.role}]",
                 font=("Segoe UI", 9, "bold"),
                 bg=C["surface"], fg=C["text_muted"]).pack(side="left", padx=(8, 0))

    # ─────────────────────── SCALE CARD ──────────────────────────────────────
    def _build_scale_card(self, parent):
        C = self.C
        card = self._card(parent, "⚡  Live Scale Reading")
        card.pack(fill="x", pady=(0, 12))

        # Big weight display
        disp = tk.Frame(card, bg=C["scale_bg"],
                        highlightbackground=C["border"], highlightthickness=1)
        disp.pack(fill="x", padx=16, pady=10)

        self._weight_lbl = tk.Label(disp, text="0.000",
                                    font=("Courier New", 44, "bold"),
                                    bg=C["scale_bg"], fg=C["accent2"])
        self._weight_lbl.pack(pady=(16, 0))
        self._unit_lbl = tk.Label(disp, text="kg",
                                  font=("Segoe UI", 14),
                                  bg=C["scale_bg"], fg=C["text_muted"])
        self._unit_lbl.pack(pady=(0, 6))

        # Ton equivalent
        self._ton_lbl = tk.Label(disp, text="0.000 ton",
                                 font=("Segoe UI", 11),
                                 bg=C["scale_bg"], fg=C["text_muted"])
        self._ton_lbl.pack(pady=(0, 16))

        # Slider (simulate scale)
        tk.Label(card, text="Simulate Scale Input (kg)",
                 font=("Segoe UI", 8), bg=C["card"],
                 fg=C["text_muted"]).pack(anchor="w", padx=16)

        self._slider = ttk.Scale(card, from_=0, to=60000,
                                 orient="horizontal",
                                 command=self._on_slider)
        self._slider.pack(fill="x", padx=16, pady=(4, 4))

        # Quick weight buttons
        qf = tk.Frame(card, bg=C["card"])
        qf.pack(fill="x", padx=16, pady=(0, 14))
        for w, lbl in [(5000, "5 T"), (10000, "10 T"),
                       (20000, "20 T"), (40000, "40 T")]:
            b = tk.Button(qf, text=lbl, font=("Segoe UI", 9),
                          bg=C["btn_bg"], fg=C["text"], relief="flat",
                          bd=0, cursor="hand2",
                          command=lambda v=w: self._set_weight(v), padx=8)
            b.pack(side="left", padx=(0, 6))

        tk.Button(qf, text="⟳ Zero", font=("Segoe UI", 9),
                  bg=C["danger"], fg="#fff", relief="flat",
                  bd=0, cursor="hand2",
                  command=lambda: self._set_weight(0)).pack(side="right")

    def _on_slider(self, val):
        self._target_weight = float(val)

    def _set_weight(self, val):
        self._target_weight = float(val)
        self._slider.set(val)

    def _animate_scale(self):
        current = self._simulated_weight.get()
        diff = self._target_weight - current
        step = diff * 0.15
        if abs(diff) < 0.5:
            step = diff
        new_val = current + step
        self._simulated_weight.set(new_val)
        self._weight_lbl.configure(text=f"{new_val:,.1f}")
        self._ton_lbl.configure(text=f"{kg_to_ton(new_val):.3f} ton")
        self.after(40, self._animate_scale)

    def _get_current_weight(self):
        return round(self._simulated_weight.get(), 2)

    # ──────────────────────── FORM CARD ──────────────────────────────────────
    def _build_form_card(self, parent):
        C = self.C
        card = self._card(parent, "📋  Weighment Entry")
        card.pack(fill="both", expand=True)

        # Notebook tabs: New Entry / Exit Weigh
        tab_frame = tk.Frame(card, bg=C["card"])
        tab_frame.pack(fill="x", padx=16, pady=(0, 10))

        self._tab_var = tk.IntVar(value=0)
        for i, lbl in enumerate(["🟢  Entry Weigh", "🔴  Exit Weigh"]):
            rb = tk.Radiobutton(tab_frame, text=lbl,
                                variable=self._tab_var, value=i,
                                font=("Segoe UI", 9, "bold"),
                                bg=C["card"], fg=C["text"],
                                activebackground=C["card"],
                                selectcolor=C["highlight"],
                                indicatoron=False,
                                relief="flat", bd=0,
                                cursor="hand2", padx=14, pady=6,
                                command=self._on_tab_change)
            rb.pack(side="left", padx=(0, 6))

        # ── Form fields ──
        form = tk.Frame(card, bg=C["card"])
        form.pack(fill="both", expand=True, padx=16)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        self._fields = {}

        def row(r, label, key, col=0, width=18, editable=True):
            tk.Label(form, text=label, font=("Segoe UI", 9),
                     bg=C["card"], fg=C["text_muted"]).grid(
                row=r, column=col*2, sticky="w", pady=5)
            var = tk.StringVar()
            state = "normal" if editable else "readonly"
            e = tk.Entry(form, textvariable=var, font=("Segoe UI", 10),
                         bg=C["entry_bg"], fg=C["text"],
                         insertbackground=C["text"],
                         relief="flat", bd=0,
                         highlightbackground=C["border"],
                         highlightthickness=1, width=width,
                         state=state)
            e.grid(row=r, column=col*2+1, sticky="ew", padx=(8, 16), pady=5)
            self._fields[key] = var
            return var

        row(0, "Ticket No *",   "ticket_no", 0, editable=False)
        row(0, "Vehicle No *",  "vehicle_no", 1)
        row(1, "Driver Name",   "driver_name", 0)
        row(1, "Material *",    "material", 1)
        row(2, "Supplier",      "supplier", 0)
        row(2, "Party / Client","party", 1)
        row(3, "Remarks",       "remarks", 0)

        # Weight capture buttons
        wf = tk.Frame(card, bg=C["card"])
        wf.pack(fill="x", padx=16, pady=8)

        self._gross_lbl = self._weight_badge(wf, "GROSS WT", "—", C["accent"])
        self._gross_lbl.pack(side="left", padx=(0, 10))
        self._tare_lbl  = self._weight_badge(wf, "TARE WT",  "—", C["warning"])
        self._tare_lbl .pack(side="left", padx=(0, 10))
        self._net_lbl   = self._weight_badge(wf, "NET WT",   "—", C["accent2"])
        self._net_lbl  .pack(side="left")

        # Action buttons
        btnf = tk.Frame(card, bg=C["card"])
        btnf.pack(fill="x", padx=16, pady=(4, 16))

        tk.Button(btnf, text="⬇  CAPTURE WEIGHT",
                  font=("Segoe UI", 10, "bold"),
                  bg=C["accent"], fg="#fff", relief="flat", bd=0,
                  cursor="hand2", command=self._capture_weight, padx=16, pady=8
                  ).pack(side="left", padx=(0, 8))

        tk.Button(btnf, text="✔  SAVE TICKET",
                  font=("Segoe UI", 10, "bold"),
                  bg=C["accent2"], fg="#fff", relief="flat", bd=0,
                  cursor="hand2", command=self._save_ticket, padx=16, pady=8
                  ).pack(side="left", padx=(0, 8))

        tk.Button(btnf, text="✚  NEW TICKET",
                  font=("Segoe UI", 10, "bold"),
                  bg=C["btn_bg"], fg=C["text"], relief="flat", bd=0,
                  cursor="hand2", command=self._new_ticket, padx=16, pady=8
                  ).pack(side="left", padx=(0, 8))

        tk.Button(btnf, text="🖨  PRINT",
                  font=("Segoe UI", 10, "bold"),
                  bg=C["btn_bg"], fg=C["text"], relief="flat", bd=0,
                  cursor="hand2", command=self._print_ticket, padx=16, pady=8
                  ).pack(side="left")

        self._captured_gross = 0.0
        self._captured_tare  = 0.0
        self._new_ticket()

    def _weight_badge(self, parent, label, value, color):
        C = self.C
        f = tk.Frame(parent, bg=C["card"],
                     highlightbackground=color, highlightthickness=1)
        tk.Label(f, text=label, font=("Segoe UI", 7, "bold"),
                 bg=C["card"], fg=color).pack(padx=8, pady=(4, 0))
        lbl = tk.Label(f, text=value, font=("Courier New", 13, "bold"),
                       bg=C["card"], fg=C["text"])
        lbl.pack(padx=8, pady=(0, 4))
        f._value_lbl = lbl
        return f

    def _on_tab_change(self):
        # If exit tab, lookup by vehicle no
        pass

    def _new_ticket(self):
        for k, v in self._fields.items():
            v.set("")
        self._fields["ticket_no"].set(generate_ticket())
        self._captured_gross = 0.0
        self._captured_tare  = 0.0
        self._tab_var.set(0)
        self._update_weight_badges()

    def _capture_weight(self):
        w = self._get_current_weight()
        if self._tab_var.get() == 0:
            self._captured_gross = w
        else:
            self._captured_tare = w
        self._update_weight_badges()

    def _update_weight_badges(self):
        net = max(0, self._captured_gross - self._captured_tare)
        self._gross_lbl._value_lbl.configure(
            text=f"{self._captured_gross:,.1f} kg")
        self._tare_lbl._value_lbl.configure(
            text=f"{self._captured_tare:,.1f} kg")
        self._net_lbl._value_lbl.configure(
            text=f"{net:,.1f} kg")

    def _save_ticket(self):
        vno = self._fields["vehicle_no"].get().strip().upper()
        mat = self._fields["material"].get().strip()
        if not vno:
            messagebox.showwarning("Validation", "Vehicle No is required.")
            return
        if not mat:
            messagebox.showwarning("Validation", "Material is required.")
            return

        ticket = self._fields["ticket_no"].get().strip()
        net = max(0, self._captured_gross - self._captured_tare)

        conn = get_conn()
        c = conn.cursor()

        # Check if ticket already exists (exit weigh update)
        existing = c.execute(
            "SELECT id FROM transactions WHERE ticket_no=?", (ticket,)).fetchone()

        if existing:
            c.execute("""
                UPDATE transactions SET
                    tare_wt=?, net_wt=?, exit_time=?, status='OUT',
                    remarks=?
                WHERE ticket_no=?
            """, (self._captured_tare, net,
                  now_str(), self._fields["remarks"].get(), ticket))
        else:
            c.execute("""
                INSERT INTO transactions
                (ticket_no,vehicle_no,driver_name,material,supplier,party,
                 gross_wt,tare_wt,net_wt,entry_time,status,operator,remarks)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                ticket, vno,
                self._fields["driver_name"].get(),
                mat,
                self._fields["supplier"].get(),
                self._fields["party"].get(),
                self._captured_gross,
                self._captured_tare,
                net,
                now_str(), "IN", self.operator,
                self._fields["remarks"].get()
            ))
        conn.commit()
        conn.close()
        messagebox.showinfo("Saved", f"Ticket {ticket} saved successfully.")
        self._refresh_table()
        self._new_ticket()

    def _print_ticket(self):
        ticket = self._fields["ticket_no"].get().strip()
        vno    = self._fields["vehicle_no"].get().strip()
        if not ticket and not vno:
            messagebox.showinfo("Print", "No ticket to print.")
            return
        net = max(0, self._captured_gross - self._captured_tare)
        txt = (
            f"{'='*42}\n"
            f"   {APP_TITLE}  —  WEIGH TICKET\n"
            f"{'='*42}\n"
            f"  Ticket No  : {ticket}\n"
            f"  Date/Time  : {now_str()}\n"
            f"  Vehicle No : {vno}\n"
            f"  Driver     : {self._fields['driver_name'].get()}\n"
            f"  Material   : {self._fields['material'].get()}\n"
            f"  Supplier   : {self._fields['supplier'].get()}\n"
            f"  Party      : {self._fields['party'].get()}\n"
            f"{'-'*42}\n"
            f"  Gross Wt   : {self._captured_gross:>10,.2f} kg\n"
            f"  Tare  Wt   : {self._captured_tare:>10,.2f} kg\n"
            f"  Net   Wt   : {net:>10,.2f} kg\n"
            f"             : {kg_to_ton(net):>10.3f} ton\n"
            f"{'-'*42}\n"
            f"  Operator   : {self.operator}\n"
            f"  Remarks    : {self._fields['remarks'].get()}\n"
            f"{'='*42}\n"
        )
        self._show_print_dialog(txt)

    def _show_print_dialog(self, content):
        C = self.C
        win = tk.Toplevel(self)
        win.title("Weigh Ticket — Print Preview")
        win.configure(bg=C["bg"])
        win.geometry("460x480")
        t = tk.Text(win, font=("Courier New", 10), bg=C["surface"],
                    fg=C["text"], relief="flat", bd=0,
                    padx=10, pady=10)
        t.pack(fill="both", expand=True, padx=16, pady=16)
        t.insert("1.0", content)
        t.configure(state="disabled")
        tk.Button(win, text="Close", font=("Segoe UI", 10),
                  bg=C["btn_bg"], fg=C["text"], relief="flat",
                  bd=0, cursor="hand2", command=win.destroy,
                  padx=20, pady=6).pack(pady=(0, 16))

    # ─────────────────────── HISTORY PANEL ───────────────────────────────────
    def _build_history_panel(self, parent):
        C = self.C
        card = self._card(parent, "📑  Transaction History")
        card.pack(fill="both", expand=True)

        # Search bar
        sf = tk.Frame(card, bg=C["card"])
        sf.pack(fill="x", padx=16, pady=(4, 8))

        tk.Label(sf, text="🔍", font=("Segoe UI", 11),
                 bg=C["card"], fg=C["text_muted"]).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_table())
        tk.Entry(sf, textvariable=self._search_var,
                 font=("Segoe UI", 10), bg=C["entry_bg"],
                 fg=C["text"], insertbackground=C["text"],
                 relief="flat", bd=0,
                 highlightbackground=C["border"],
                 highlightthickness=1).pack(
            side="left", fill="x", expand=True, ipady=6, padx=(6, 10))

        # Status filter
        self._status_var = tk.StringVar(value="ALL")
        for s, lbl in [("ALL", "All"), ("IN", "In"), ("OUT", "Out")]:
            tk.Radiobutton(sf, text=lbl, variable=self._status_var, value=s,
                           font=("Segoe UI", 9),
                           bg=C["card"], fg=C["text"],
                           activebackground=C["card"],
                           selectcolor=C["highlight"],
                           indicatoron=False,
                           relief="flat", bd=0, padx=8, pady=4,
                           cursor="hand2",
                           command=self._refresh_table).pack(side="left", padx=2)

        # Treeview
        cols = ("Ticket", "Vehicle", "Material", "Gross kg",
                "Tare kg", "Net kg", "Net ton", "Status",
                "Entry Time", "Operator")
        self._tree = ttk.Treeview(card, columns=cols, show="headings",
                                  selectmode="browse")

        widths = [130, 90, 90, 80, 80, 80, 70, 60, 140, 80]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col,
                               command=lambda c=col: self._sort_tree(c, False))
            self._tree.column(col, width=w, anchor="center")

        # Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=C["surface"],
                        foreground=C["text"],
                        rowheight=28,
                        fieldbackground=C["surface"],
                        bordercolor=C["border"],
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=C["card"],
                        foreground=C["text_muted"],
                        borderwidth=0,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview",
                  background=[("selected", C["highlight"])],
                  foreground=[("selected", "#ffffff")])

        vsb = ttk.Scrollbar(card, orient="vertical",
                             command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=8)
        vsb.pack(side="right", fill="y", pady=8, padx=(0, 8))

        self._tree.tag_configure("IN",  background="#0d2137",
                                 foreground=C["accent"])
        self._tree.tag_configure("OUT", background="#0d2b13",
                                 foreground=C["accent2"])

        # Bottom stats bar
        self._stats_var = tk.StringVar()
        tk.Label(card, textvariable=self._stats_var,
                 font=("Segoe UI", 9), bg=C["card"],
                 fg=C["text_muted"]).pack(anchor="w", padx=16, pady=(0, 8))

        # Double-click to load
        self._tree.bind("<Double-1>", self._load_from_history)

    def _refresh_table(self):
        search = self._search_var.get().strip().lower()
        status = self._status_var.get()

        for row in self._tree.get_children():
            self._tree.delete(row)

        conn = get_conn()
        rows = conn.execute("""
            SELECT ticket_no, vehicle_no, material,
                   gross_wt, tare_wt, net_wt,
                   status, entry_time, operator
            FROM transactions
            ORDER BY id DESC
        """).fetchall()
        conn.close()

        total_net = 0
        count = 0
        for r in rows:
            (ticno, vno, mat, gross, tare, net,
             st, etime, op) = r
            if status != "ALL" and st != status:
                continue
            if search and search not in (
                    f"{ticno}{vno}{mat}{op}".lower()):
                continue
            tag = st if st in ("IN", "OUT") else ""
            self._tree.insert("", "end", values=(
                ticno, vno, mat,
                f"{gross:,.1f}", f"{tare:,.1f}", f"{net:,.1f}",
                f"{kg_to_ton(net):.3f}",
                st, etime or "—", op or "—"
            ), tags=(tag,))
            total_net += net
            count += 1

        self._stats_var.set(
            f"  {count} records  |  Total Net: {total_net:,.1f} kg  "
            f"({kg_to_ton(total_net):.3f} ton)"
        )

    def _sort_tree(self, col, reverse):
        data = [(self._tree.set(k, col), k)
                for k in self._tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0].replace(",", "")),
                      reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)
        for i, (_, k) in enumerate(data):
            self._tree.move(k, "", i)
        self._tree.heading(col,
                           command=lambda: self._sort_tree(col, not reverse))

    def _load_from_history(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0])["values"]
        ticket = vals[0]
        conn = get_conn()
        row = conn.execute("""
            SELECT ticket_no,vehicle_no,driver_name,material,
                   supplier,party,gross_wt,tare_wt,remarks
            FROM transactions WHERE ticket_no=?
        """, (ticket,)).fetchone()
        conn.close()
        if not row:
            return
        (ticno, vno, drv, mat, sup, party,
         gross, tare, rem) = row
        self._fields["ticket_no"].set(ticno)
        self._fields["vehicle_no"].set(vno)
        self._fields["driver_name"].set(drv or "")
        self._fields["material"].set(mat or "")
        self._fields["supplier"].set(sup or "")
        self._fields["party"].set(party or "")
        self._fields["remarks"].set(rem or "")
        self._captured_gross = gross
        self._captured_tare  = tare
        self._update_weight_badges()
        self._tab_var.set(1)   # switch to exit tab

    # ─────────────────────── EXPORT ──────────────────────────────────────────
    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All", "*.*")],
            initialfile=f"weightbridge_export_{datetime.date.today()}.csv"
        )
        if not path:
            return
        conn = get_conn()
        rows = conn.execute("""
            SELECT ticket_no,vehicle_no,driver_name,material,
                   supplier,party,gross_wt,tare_wt,net_wt,
                   entry_time,exit_time,status,operator,remarks
            FROM transactions ORDER BY id DESC
        """).fetchall()
        conn.close()
        headers = ["Ticket No", "Vehicle No", "Driver", "Material",
                   "Supplier", "Party", "Gross (kg)", "Tare (kg)",
                   "Net (kg)", "Entry Time", "Exit Time",
                   "Status", "Operator", "Remarks"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)
        messagebox.showinfo("Export", f"Exported {len(rows)} records to:\n{path}")

    # ─────────────────────── THEME TOGGLE ────────────────────────────────────
    def _toggle_theme(self):
        # Simple notification — full re-theme requires restart
        if self.theme == "dark":
            self.theme = "light"
            self._theme_btn.configure(text="🌙 Dark")
            messagebox.showinfo("Theme", "Light theme will apply on next launch.\n"
                                         "(Full theme switching coming in v2.0)")
        else:
            self.theme = "dark"
            self._theme_btn.configure(text="☀ Light")

    # ─────────────────────── UTILITY ─────────────────────────────────────────
    def _card(self, parent, title):
        C = self.C
        outer = tk.Frame(parent, bg=C["card"],
                         highlightbackground=C["border"],
                         highlightthickness=1)
        tk.Label(outer, text=title, font=("Segoe UI", 10, "bold"),
                 bg=C["card"], fg=C["text"]).pack(
            anchor="w", padx=16, pady=(12, 4))
        tk.Frame(outer, bg=C["border"], height=1).pack(fill="x")
        return outer

    def _on_close(self):
        if messagebox.askyesno("Exit", "Exit WeighBridge Pro?"):
            self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
#                                  MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    init_db()
    app = LoginWindow()
    app.mainloop()
