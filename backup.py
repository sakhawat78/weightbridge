"""
backup.py — Database Backup & Restore for WeighBridge Pro

• Auto-backup on configurable schedule (daily by default)
• Manual backup / restore
• Keeps last 30 backups; prunes oldest automatically
"""

import shutil
import threading
import datetime
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

DB_PATH     = BASE_DIR / "weightbridge.db"
BACKUP_DIR  = BASE_DIR / "backups"
MAX_BACKUPS = 30


class BackupManager:
    def __init__(self, interval_hours: float = 24.0):
        self.interval_hours = interval_hours
        self._timer = None
        BACKUP_DIR.mkdir(exist_ok=True)

    # ─────────────────── AUTO BACKUP ──────────────────────────────────────
    def start_scheduler(self):
        """Start the recurring auto-backup timer."""
        self._schedule_next()

    def _schedule_next(self):
        secs = self.interval_hours * 3600
        self._timer = threading.Timer(secs, self._auto_backup_tick)
        self._timer.daemon = True
        self._timer.start()

    def _auto_backup_tick(self):
        try:
            self.auto_backup()
        finally:
            self._schedule_next()

    def stop_scheduler(self):
        if self._timer:
            self._timer.cancel()

    # ─────────────────── BACKUP ───────────────────────────────────────────
    def auto_backup(self) -> Path:
        """Create a timestamped backup and prune old ones."""
        BACKUP_DIR.mkdir(exist_ok=True)
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = BACKUP_DIR / f"wb_{ts}.db"
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, dest)
        self._prune()
        return dest

    def manual_backup(self, dest_path: str) -> bool:
        """Copy DB to a user-specified path."""
        try:
            shutil.copy2(DB_PATH, dest_path)
            return True
        except Exception:
            return False

    # ─────────────────── RESTORE ──────────────────────────────────────────
    def restore(self, src_path: str) -> bool:
        """Overwrite current DB with a backup."""
        try:
            # First backup the current DB just in case
            self.auto_backup()
            shutil.copy2(src_path, DB_PATH)
            return True
        except Exception:
            return False

    # ─────────────────── PRUNE ────────────────────────────────────────────
    def _prune(self):
        files = sorted(BACKUP_DIR.glob("wb_*.db"),
                       key=lambda f: f.stat().st_mtime)
        while len(files) > MAX_BACKUPS:
            files.pop(0).unlink(missing_ok=True)

    # ─────────────────── LISTING ──────────────────────────────────────────
    def list_backups(self) -> list:
        BACKUP_DIR.mkdir(exist_ok=True)
        files = sorted(BACKUP_DIR.glob("wb_*.db"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
        return [
            {
                "name": f.name,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "mtime": datetime.datetime.fromtimestamp(
                    f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for f in files
        ]
