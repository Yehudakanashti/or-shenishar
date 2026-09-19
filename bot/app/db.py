"""שכבת הנתונים: SQLite מקומי. אין שום דבר בענן."""
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .config import (
    BUSINESS_DEFAULTS, DATA_DIR, DB_PATH, DEFAULT_SETTINGS, SCHEMA_PATH, TIMEZONE, UPLOAD_DIR,
)


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# עמודות שנוספו אחרי הגרסה הראשונה — מתווספות למסד קיים בלי למחוק נתונים
MIGRATIONS = {
    "products": {"occasion": "TEXT NOT NULL DEFAULT \'\'",
                 "season_start": "TEXT NOT NULL DEFAULT \'\'",
                 "season_end": "TEXT NOT NULL DEFAULT \'\'"},
}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, columns in MIGRATIONS.items():
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        for column, ddl in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _migrate(conn)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO NOTHING",
                (key, value),
            )


def now_local() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


# ---------- settings ----------

def get_settings() -> dict[str, str]:
    with connect() as conn:
        return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")}


def business() -> dict[str, str]:
    """זהות העסק כפי שנערכה בהגדרות — מזינה את הפרומפט ואת כותרת הממשק."""
    current = get_settings()
    return {key: (current.get(key) or default) for key, default in BUSINESS_DEFAULTS.items()}


def get_setting(key: str, default: str = "") -> str:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings(key, value, updated_at) VALUES(?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
            (key, str(value)),
        )


def setting_int(key: str, default: int) -> int:
    try:
        return int(get_setting(key, str(default)))
    except ValueError:
        return default


def setting_float(key: str, default: float) -> float:
    try:
        return float(get_setting(key, str(default)))
    except ValueError:
        return default


def setting_bool(key: str, default: bool = False) -> bool:
    return get_setting(key, "on" if default else "off") in ("1", "on", "true", "yes")


# ---------- events ----------

def log_event(kind: str, summary: str = "", payload: dict[str, Any] | None = None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO events(kind, summary, payload) VALUES(?, ?, ?)",
            (kind, summary, json.dumps(payload or {}, ensure_ascii=False)),
        )


def recent_events(limit: int = 100) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


# ---------- products ----------

def list_products(active_only: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM products"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY line, name"
    with connect() as conn:
        rows = conn.execute(sql).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["keywords"] = json.loads(item["keywords"] or "[]")
            item["images"] = [
                dict(i)
                for i in conn.execute(
                    "SELECT * FROM product_images WHERE product_id = ? ORDER BY is_primary DESC, id",
                    (row["id"],),
                ).fetchall()
            ]
            out.append(item)
    return out


def get_product(product_id: int) -> dict[str, Any] | None:
    for item in list_products():
        if item["id"] == product_id:
            return item
    return None


def get_product_by_slug(slug: str) -> dict[str, Any] | None:
    for item in list_products():
        if item["slug"] == slug:
            return item
    return None


def upsert_product(data: dict[str, Any], product_id: int | None = None) -> int:
    fields = (
        "slug", "name", "line", "tagline", "description", "audience", "price_from",
        "price_to", "lead_time", "shipping", "customization", "order_url", "keywords",
        "occasion", "season_start", "season_end", "notes", "active",
    )
    payload = {k: data.get(k) for k in fields}
    payload["keywords"] = json.dumps(data.get("keywords") or [], ensure_ascii=False)
    with connect() as conn:
        if product_id:
            sets = ", ".join(f"{k} = :{k}" for k in fields)
            conn.execute(f"UPDATE products SET {sets} WHERE id = :id", {**payload, "id": product_id})
            return product_id
        cols = ", ".join(fields)
        marks = ", ".join(f":{k}" for k in fields)
        cur = conn.execute(f"INSERT INTO products({cols}) VALUES({marks})", payload)
        return int(cur.lastrowid)


def delete_product(product_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))


def add_image(product_id: int, filename: str, caption: str = "", primary: bool = False) -> int:
    with connect() as conn:
        if primary:
            conn.execute("UPDATE product_images SET is_primary = 0 WHERE product_id = ?", (product_id,))
        cur = conn.execute(
            "INSERT INTO product_images(product_id, filename, caption, is_primary) VALUES(?, ?, ?, ?)",
            (product_id, filename, caption, 1 if primary else 0),
        )
        has_primary = conn.execute(
            "SELECT COUNT(*) c FROM product_images WHERE product_id = ? AND is_primary = 1", (product_id,)
        ).fetchone()["c"]
        if not has_primary:
            conn.execute("UPDATE product_images SET is_primary = 1 WHERE id = ?", (cur.lastrowid,))
        return int(cur.lastrowid)


def get_image(image_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM product_images WHERE id = ?", (image_id,)).fetchone()
    return dict(row) if row else None


def set_primary_image(image_id: int) -> None:
    with connect() as conn:
        row = conn.execute("SELECT product_id FROM product_images WHERE id = ?", (image_id,)).fetchone()
        if not row:
            return
        conn.execute("UPDATE product_images SET is_primary = 0 WHERE product_id = ?", (row["product_id"],))
        conn.execute("UPDATE product_images SET is_primary = 1 WHERE id = ?", (image_id,))


def delete_image(image_id: int) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM product_images WHERE id = ?", (image_id,)).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM product_images WHERE id = ?", (image_id,))
        return row["filename"]


def primary_image_for(product_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM product_images WHERE product_id = ? ORDER BY is_primary DESC, id LIMIT 1",
            (product_id,),
        ).fetchone()
    return dict(row) if row else None


# ---------- posts & suggestions ----------

def find_post_by_hash(text_hash: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM posts WHERE text_hash = ?", (text_hash,)).fetchone()
    return dict(row) if row else None


def insert_post(text: str, text_hash: str, group_name: str, author_name: str, url: str, source: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO posts(text, text_hash, group_name, author_name, url, source) VALUES(?, ?, ?, ?, ?, ?)",
            (text, text_hash, group_name, author_name, url, source),
        )
        return int(cur.lastrowid)


def insert_suggestion(data: dict[str, Any]) -> int:
    fields = (
        "post_id", "product_id", "image_id", "relevant", "intent", "sensitivity",
        "confidence", "comment_text", "dm_text", "reasoning", "needs_human",
        "policy_notes", "status", "engine", "usage_in", "usage_out",
    )
    payload = {k: data.get(k) for k in fields}
    payload["policy_notes"] = json.dumps(data.get("policy_notes") or [], ensure_ascii=False)
    cols = ", ".join(fields)
    marks = ", ".join(f":{k}" for k in fields)
    with connect() as conn:
        cur = conn.execute(f"INSERT INTO suggestions({cols}) VALUES({marks})", payload)
        return int(cur.lastrowid)


def _hydrate_suggestion(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["policy_notes"] = json.loads(item["policy_notes"] or "[]")
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (item["post_id"],)).fetchone()
    item["post"] = dict(post) if post else {}
    item["product"] = None
    if item["product_id"]:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (item["product_id"],)).fetchone()
        if product:
            item["product"] = dict(product)
    item["image"] = None
    if item["image_id"]:
        image = conn.execute("SELECT * FROM product_images WHERE id = ?", (item["image_id"],)).fetchone()
        if image:
            item["image"] = dict(image)
    return item


def list_suggestions(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    sql = "SELECT * FROM suggestions"
    params: list[Any] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        return [_hydrate_suggestion(conn, r) for r in conn.execute(sql, params).fetchall()]


def get_suggestion(suggestion_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM suggestions WHERE id = ?", (suggestion_id,)).fetchone()
        return _hydrate_suggestion(conn, row) if row else None


def decide_suggestion(suggestion_id: int, status: str, final_comment: str = "", final_dm: str = "") -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE suggestions SET status = ?, final_comment = ?, final_dm = ?, decided_at = datetime('now') "
            "WHERE id = ?",
            (status, final_comment, final_dm, suggestion_id),
        )


def update_suggestion_media(suggestion_id: int, product_id: int | None, image_id: int | None) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE suggestions SET product_id = ?, image_id = ? WHERE id = ?",
            (product_id, image_id, suggestion_id),
        )


def suggestions_today() -> int:
    start = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) c FROM suggestions WHERE created_at >= ?",
            (start.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S"),),
        ).fetchone()
    return int(row["c"])


def recent_author_suggestion(author_name: str, days: int) -> dict[str, Any] | None:
    if not author_name.strip():
        return None
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with connect() as conn:
        row = conn.execute(
            "SELECT s.* FROM suggestions s JOIN posts p ON p.id = s.post_id "
            "WHERE p.author_name = ? AND s.created_at >= ? AND s.status IN ('pending','approved') "
            "ORDER BY s.id DESC LIMIT 1",
            (author_name.strip(), since),
        ).fetchone()
    return dict(row) if row else None


def stats() -> dict[str, int]:
    with connect() as conn:
        def count(sql: str, params: Iterable[Any] = ()) -> int:
            return int(conn.execute(sql, tuple(params)).fetchone()["c"])

        return {
            "pending": count("SELECT COUNT(*) c FROM suggestions WHERE status = 'pending'"),
            "approved": count("SELECT COUNT(*) c FROM suggestions WHERE status = 'approved'"),
            "rejected": count("SELECT COUNT(*) c FROM suggestions WHERE status = 'rejected'"),
            "products": count("SELECT COUNT(*) c FROM products WHERE active = 1"),
            "images": count("SELECT COUNT(*) c FROM product_images"),
            "examples": count("SELECT COUNT(*) c FROM examples WHERE active = 1"),
        }


# ---------- examples (לימוד הטון) ----------

def add_example(kind: str, text: str, post_text: str = "", origin: str = "approved") -> None:
    text = (text or "").strip()
    if not text:
        return
    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM examples WHERE kind = ? AND text = ?", (kind, text)
        ).fetchone()
        if exists:
            return
        conn.execute(
            "INSERT INTO examples(kind, post_text, text, origin) VALUES(?, ?, ?, ?)",
            (kind, post_text[:600], text, origin),
        )


def list_examples(kind: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    sql = "SELECT * FROM examples WHERE active = 1"
    params: list[Any] = []
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def delete_example(example_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM examples WHERE id = ?", (example_id,))


# ---------- blocklist ----------

def list_blocklist() -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM blocklist ORDER BY kind, value")]


def add_block(kind: str, value: str, note: str = "") -> None:
    value = (value or "").strip()
    if not value:
        return
    with connect() as conn:
        conn.execute(
            "INSERT INTO blocklist(kind, value, note) VALUES(?, ?, ?) ON CONFLICT(kind, value) DO NOTHING",
            (kind, value, note),
        )


def delete_block(block_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM blocklist WHERE id = ?", (block_id,))
