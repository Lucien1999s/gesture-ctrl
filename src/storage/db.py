import os
import sqlite3
import platform
from typing import List, Optional

APP_DIR_NAME = "gesture-ctrl"

def _app_data_dir() -> str:
    system = platform.system().lower()
    home = os.path.expanduser("~")
    if "darwin" in system or "mac" in system:
        base = os.path.join(home, "Library", "Application Support", APP_DIR_NAME)
    elif "windows" in system:
        base = os.path.join(os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming")), APP_DIR_NAME)
    else:
        base = os.path.join(home, ".local", "share", APP_DIR_NAME)
    os.makedirs(base, exist_ok=True)
    return base

def _db_path() -> str:
    return os.path.join(_app_data_dir(), "gesture.db")

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS urls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  url  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""

class UrlStore:
    """SQLite-backed URL presets with an active selection (limit 10 entries)."""
    LIMIT = 10
    DEFAULT_NAME = "YouTube"
    DEFAULT_URL = "https://www.youtube.com/"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _db_path()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    @property
    def path(self) -> str:
        """Absolute filesystem path to the SQLite database file."""
        return self.db_path

    def _init_db(self):
        with self.conn:
            self.conn.executescript(_SCHEMA)
        # Seed defaults if empty
        if not self.list_urls():
            self.add_url(self.DEFAULT_NAME, self.DEFAULT_URL)
            self.set_active_name(self.DEFAULT_NAME)

    # ---------- CRUD ----------
    def list_urls(self):
        cur = self.conn.execute("SELECT id,name,url FROM urls ORDER BY id ASC")
        return cur.fetchall()

    def list_names(self) -> List[str]:
        return [row["name"] for row in self.list_urls()]

    def get_url(self, name: str) -> Optional[str]:
        cur = self.conn.execute("SELECT url FROM urls WHERE name = ?", (name,))
        row = cur.fetchone()
        return row["url"] if row else None

    def count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) AS c FROM urls")
        return cur.fetchone()["c"]

    def add_url(self, name: str, url: str) -> None:
        if self.count() >= self.LIMIT:
            raise ValueError(f"Maximum of {self.LIMIT} URLs reached")
        with self.conn:
            self.conn.execute("INSERT INTO urls(name,url) VALUES(?,?)", (name, url))

    def update_url(self, old_name: str, new_name: str, new_url: str) -> None:
        with self.conn:
            if old_name != new_name:
                cur = self.conn.execute("SELECT 1 FROM urls WHERE name=?", (new_name,))
                if cur.fetchone():
                    raise ValueError("Name already exists")
            self.conn.execute(
                "UPDATE urls SET name=?, url=? WHERE name=?",
                (new_name, new_url, old_name),
            )
            # Keep active selection consistent if renamed
            cur = self.conn.execute("SELECT value FROM settings WHERE key='active_url'")
            row = cur.fetchone()
            if row and row["value"] == old_name:
                self.set_active_name(new_name)

    def delete_url(self, name: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM urls WHERE name=?", (name,))
            # If deleting active, fall back to first remaining row
            cur = self.conn.execute("SELECT value FROM settings WHERE key='active_url'")
            row = cur.fetchone()
            if row and row["value"] == name:
                names = self.list_names()
                self.set_active_name(names[0] if names else self.DEFAULT_NAME)

    # ---------- active selection ----------
    def set_active_name(self, name: str) -> None:
        if not self.get_url(name):
            raise ValueError("URL name not found")
        with self.conn:
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES('active_url',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (name,),
            )

    def get_active_name(self) -> str:
        cur = self.conn.execute("SELECT value FROM settings WHERE key='active_url'")
        row = cur.fetchone()
        return row["value"] if row else self.DEFAULT_NAME

    def get_active_url(self) -> str:
        name = self.get_active_name()
        url = self.get_url(name)
        return url or self.DEFAULT_URL

    # ---------- utils ----------
    def ensure(self, name: str, url: str) -> None:
        """Ensure a (name,url) exists; create if missing (respects LIMIT)."""
        if self.get_url(name):
            return
        self.add_url(name, url)

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass
