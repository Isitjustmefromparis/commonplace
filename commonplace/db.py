"""Couche SQLite de CommonPlace. stdlib uniquement."""
import sqlite3
import re
from datetime import datetime, timezone
from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url          TEXT UNIQUE NOT NULL,
    platform     TEXT,
    source       TEXT,            -- telegram | youtube
    author       TEXT,
    title        TEXT,
    caption      TEXT,            -- legende / description
    duration     INTEGER,
    video_path   TEXT,            -- chemin relatif a data/
    thumb_path   TEXT,            -- chemin relatif a data/
    captured_at  TEXT,
    downloaded_at TEXT,
    classified_at TEXT,
    status       TEXT DEFAULT 'new',  -- new|downloaded|metadata_only|error
    error        TEXT
);

CREATE TABLE IF NOT EXISTS lists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS bookmark_lists (
    bookmark_id INTEGER NOT NULL,
    list_id     INTEGER NOT NULL,
    PRIMARY KEY (bookmark_id, list_id),
    FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE,
    FOREIGN KEY (list_id)     REFERENCES lists(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    config.ensure_dirs()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


# --- meta (offset Telegram, etc.) ---
def meta_get(conn, key, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def meta_set(conn, key, value):
    conn.execute(
        "INSERT INTO meta(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    conn.commit()


# --- bookmarks ---
def slugify(text):
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:60] or "liste"


def detect_platform(url):
    u = url.lower()
    if "tiktok." in u:
        return "tiktok"
    if "instagram." in u:
        return "instagram"
    if "youtube." in u or "youtu.be" in u:
        return "youtube"
    if "twitter.com" in u or "x.com" in u or "//t.co/" in u:
        return "twitter"
    return "autre"


def add_bookmark(conn, url, source, author=None, caption=None):
    """Insere un lien s'il n'existe pas deja. Renvoie l'id ou None si doublon."""
    try:
        cur = conn.execute(
            "INSERT INTO bookmarks(url, platform, source, author, caption, "
            "captured_at, status) VALUES(?,?,?,?,?,?, 'new')",
            (url, detect_platform(url), source, author, caption, now()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None  # deja vu


def bookmarks_by_status(conn, status, limit=None):
    q = "SELECT * FROM bookmarks WHERE status=? ORDER BY id"
    if limit:
        q += f" LIMIT {int(limit)}"
    return conn.execute(q, (status,)).fetchall()


def unclassified(conn, limit=None):
    q = ("SELECT * FROM bookmarks WHERE classified_at IS NULL "
         "AND status IN ('downloaded','metadata_only') ORDER BY id")
    if limit:
        q += f" LIMIT {int(limit)}"
    return conn.execute(q).fetchall()


def update_bookmark(conn, bid, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE bookmarks SET {cols} WHERE id=?",
                 (*fields.values(), bid))
    conn.commit()


# --- lists ---
def get_or_create_list(conn, name, description=""):
    slug = slugify(name)
    row = conn.execute("SELECT id FROM lists WHERE slug=?", (slug,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO lists(slug,name,description,created_at) VALUES(?,?,?,?)",
        (slug, name, description, now()),
    )
    conn.commit()
    return cur.lastrowid


def all_lists(conn):
    return conn.execute("SELECT * FROM lists ORDER BY name").fetchall()


def link(conn, bid, list_id):
    conn.execute(
        "INSERT OR IGNORE INTO bookmark_lists(bookmark_id,list_id) VALUES(?,?)",
        (bid, list_id),
    )
    conn.commit()


def bookmarks_in_list(conn, list_id):
    return conn.execute(
        "SELECT b.* FROM bookmarks b "
        "JOIN bookmark_lists bl ON bl.bookmark_id=b.id "
        "WHERE bl.list_id=? ORDER BY b.captured_at DESC",
        (list_id,),
    ).fetchall()
