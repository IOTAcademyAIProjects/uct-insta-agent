"""
Comprehensive Database Repository for ClawAgent (SQLite & PostgreSQL Compatible)
Hardened with Parameterized Query Whitelisting, SQLite WAL Concurrency, and Datetime Normalization.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from core.security import mask_secrets

logger = logging.getLogger("clawagent.db")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "db", "uct_agent.sqlite")

ALLOWED_TABLES = {
    "posts", "drafts", "analytics_cache", "ai_calls",
    "brands", "scheduled_posts", "competitors", "trend_insights",
    "seen_dms", "campaigns", "competitor_posts", "content_ideas",
    "improvement_log"
}

def get_db_path() -> str:
    return os.getenv("DB_PATH", DEFAULT_DB_PATH)

def get_database_url() -> Optional[str]:
    return os.getenv("DATABASE_URL")

# Postgres wrapper for optional team deployment SPEC_SHEET.md:905-925
class _PostgresConnWrapper:
    """Thread-safe wrapper: new cursor per execute, safe placeholder translation."""
    def __init__(self, pg_conn):
        self._conn = pg_conn
        self._last_cursor = None
        self.row_factory = None  # compat

    def _new_cursor(self):
        try:
            import psycopg2.extras
            return self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        except Exception:
            return self._conn.cursor()

    def _translate(self, query: str) -> str:
        # Naive but safe for our codebase: no '?' inside string literals used in queries
        # For robustness, avoid touching LIKE patterns containing '?'
        if "?" not in query:
            return query
        # Only replace ? that are parameter placeholders (not inside single quotes)
        # Simple state machine: track in-string
        out = []
        in_single = False
        for ch in query:
            if ch == "'" and (not out or out[-1] != "\\"):
                in_single = not in_single
                out.append(ch)
            elif ch == "?" and not in_single:
                out.append("%s")
            else:
                out.append(ch)
        return "".join(out)

    def execute(self, query: str, params: tuple = None):
        pg_query = self._translate(query)
        if pg_query.strip().upper().startswith("PRAGMA"):
            class _Dummy:
                def fetchone(self): return None
                def fetchall(self): return []
                @property
                def lastrowid(self): return 0
                @property
                def rowcount(self): return 0
            return _Dummy()
        cur = self._new_cursor()
        self._last_cursor = cur
        cur.execute(pg_query, params or ())
        return cur

    def executemany(self, query: str, seq):
        pg_query = self._translate(query)
        cur = self._new_cursor()
        self._last_cursor = cur
        cur.executemany(pg_query, seq)
        return cur

    def commit(self):
        return self._conn.commit()

    def close(self):
        try:
            if self._last_cursor:
                self._last_cursor.close()
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)

def get_connection():
    """
    Returns DB connection: Postgres if DATABASE_URL=postgres://... else optimized SQLite WAL.
    SQLite default for solo creator ($0), Postgres for team/Agency docker-compose.
    """
    db_url = get_database_url()
    if db_url and db_url.strip().lower().startswith(("postgres://", "postgresql://")):
        try:
            import psycopg2
            import psycopg2.extras
            pg_conn = psycopg2.connect(db_url)
            pg_conn.autocommit = False
            return _PostgresConnWrapper(pg_conn)
        except ImportError:
            logger.warning("DATABASE_URL set but psycopg2 not installed — falling back to SQLite. pip install psycopg2-binary")
        except Exception as e:
            logger.warning(f"Postgres connect failed, fallback to SQLite: {mask_secrets(str(e))}")
    # SQLite fallback
    path = get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=15000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception as e:
            logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
    return conn

def normalize_datetime_to_utc(dt_str: Optional[str]) -> str:
    """Standardizes date/time strings into '%Y-%m-%d %H:%M:%S' UTC format."""
    if not dt_str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    clean = str(dt_str).strip().replace("T", " ")
    # Handle different length formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return clean

# ============================================================
# BRAND REPOSITORY
# ============================================================

def _is_pg_conn(conn) -> bool:
    return isinstance(conn, _PostgresConnWrapper)

def get_active_brand() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        # Ensure single active brand check is atomic where possible
        row = conn.execute("SELECT * FROM brands WHERE is_active = 1 LIMIT 1").fetchone()
        if row:
            return dict(row)
        
        first = conn.execute("SELECT * FROM brands ORDER BY id ASC LIMIT 1").fetchone()
        if first:
            try:
                conn.execute("UPDATE brands SET is_active = 1 WHERE id = ?", (first["id"],))
                conn.commit()
            except Exception as e:
                    logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
            return dict(first)
        
        default_name = os.getenv("BRAND_NAME", "DefaultBrand")
        try:
            if _is_pg_conn(conn):
                conn.execute(
                    """INSERT INTO brands (name, is_active, tone_of_voice, color_palette, emoji_frequency, hashtag_count_range)
                       VALUES (%s, 1, 'casual and engaging', '["#000000", "#FFFFFF"]', 2.0, '5-7') ON CONFLICT (name) DO NOTHING""",
                    (default_name,)
                )
            else:
                conn.execute(
                    """INSERT OR IGNORE INTO brands (name, is_active, tone_of_voice, color_palette, emoji_frequency, hashtag_count_range)
                       VALUES (?, 1, 'casual and engaging', '["#000000", "#FFFFFF"]', 2.0, '5-7')""",
                    (default_name,)
                )
            conn.commit()
        except Exception as e:
            # Handle race: another thread inserted same name
            if "UNIQUE" in str(e) or "duplicate" in str(e).lower():
                pass
            else:
                logger.warning(f"get_active_brand insert race: {e}")
        brand = conn.execute("SELECT * FROM brands WHERE is_active = 1 LIMIT 1").fetchone()
        if brand:
            return dict(brand)
        # Fallback re-select by name
        brand = conn.execute("SELECT * FROM brands WHERE name = ? LIMIT 1", (default_name,)).fetchone()
        if brand:
            try:
                conn.execute("UPDATE brands SET is_active = 1 WHERE id = ?", (brand["id"],))
                conn.commit()
            except Exception as e:
                    logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
            return dict(brand)
        return None
    except sqlite3.OperationalError:
        return {
            "id": 1,
            "name": "DefaultBrand",
            "tone_of_voice": "casual and engaging",
            "color_palette": "[]",
            "prohibited_words": "",
            "mandatory_elements": "",
            "sample_hooks": "[]"
        }
    finally:
        try:
            conn.close()
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")

def get_brand(brand_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM brands WHERE id = ?", (brand_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def list_brands() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM brands ORDER BY name ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def switch_active_brand(brand_name: str) -> bool:
    conn = get_connection()
    try:
        brand = conn.execute("SELECT id FROM brands WHERE LOWER(name) = LOWER(?)", (brand_name.strip(),)).fetchone()
        if not brand:
            return False
        # Atomic switch: use transaction
        try:
            # For sqlite, BEGIN IMMEDIATE ensures exclusive lock
            try:
                conn.execute("BEGIN IMMEDIATE")
            except Exception as e:
                    logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
            conn.execute("UPDATE brands SET is_active = 0")
            conn.execute("UPDATE brands SET is_active = 1 WHERE id = ?", (brand["id"],))
            conn.commit()
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception as e:
                    logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
            raise
        return True
    finally:
        try:
            conn.close()
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")

def create_brand(name: str, tone_of_voice: str = "casual", color_palette: Optional[List[str]] = None) -> int:
    conn = get_connection()
    try:
        palette_json = json.dumps(color_palette or ["#000000", "#FFFFFF"])
        cur = conn.execute(
            """INSERT INTO brands (name, is_active, tone_of_voice, color_palette)
               VALUES (?, 0, ?, ?)""",
            (name.strip(), tone_of_voice, palette_json)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

# ============================================================
# LOGGING (AI CALLS & POSTS)
# ============================================================

def log_ai_call(
    provider: str,
    model: str,
    prompt_type: str,
    success: bool,
    latency_ms: int = 0,
    error_message: Optional[str] = None,
    brand_id: Optional[int] = None
):
    conn = get_connection()
    try:
        active_b = brand_id or (get_active_brand() or {}).get("id", 1)
        safe_error = mask_secrets(error_message) if error_message else None
        conn.execute(
            """INSERT INTO ai_calls (provider, model, prompt_type, success, latency_ms, error_message, brand_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (provider, model, prompt_type, 1 if success else 0, latency_ms, safe_error, active_b)
        )
        conn.commit()
    except Exception as e:
        logger.warning(f"Could not log AI call to DB: {e}")
    finally:
        conn.close()

def log_post(
    post_id: str,
    caption: str,
    media_type: str,
    tone: str,
    image_url: str,
    provider: str,
    brand_id: Optional[int] = None,
    platform: str = "INSTAGRAM"
):
    conn = get_connection()
    try:
        active_b = brand_id or (get_active_brand() or {}).get("id", 1)
        if _is_pg_conn(conn):
            conn.execute(
                """INSERT INTO posts (post_id, caption, media_type, tone, image_url, provider, brand_id, platform, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'POSTED')
                   ON CONFLICT (post_id) DO UPDATE SET caption=EXCLUDED.caption, media_type=EXCLUDED.media_type, tone=EXCLUDED.tone, image_url=EXCLUDED.image_url, provider=EXCLUDED.provider, brand_id=EXCLUDED.brand_id, platform=EXCLUDED.platform, status='POSTED'""",
                (post_id, caption, media_type, tone, image_url, provider, active_b, platform)
            )
        else:
            conn.execute(
                """INSERT OR REPLACE INTO posts (post_id, caption, media_type, tone, image_url, provider, brand_id, platform, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'POSTED')""",
                (post_id, caption, media_type, tone, image_url, provider, active_b, platform)
            )
        conn.commit()
    except Exception as e:
        try:
            if _is_pg_conn(conn):
                conn.execute(
                    """INSERT INTO posts (post_id, caption, media_type, tone, image_url, provider)
                       VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (post_id) DO UPDATE SET caption=EXCLUDED.caption, media_type=EXCLUDED.media_type, tone=EXCLUDED.tone, image_url=EXCLUDED.image_url, provider=EXCLUDED.provider""",
                    (post_id, caption, media_type, tone, image_url, provider)
                )
            else:
                conn.execute(
                    """INSERT OR REPLACE INTO posts (post_id, caption, media_type, tone, image_url, provider)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (post_id, caption, media_type, tone, image_url, provider)
                )
            conn.commit()
        except Exception as ex:
            logger.warning(f"Could not log post to DB: {ex}")
    finally:
        try:
            conn.close()
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")

# ============================================================
# DRAFTS REPOSITORY
# ============================================================

def save_draft(
    image_url: str,
    caption: str,
    tone: str,
    media_type: str,
    brand_id: Optional[int] = None,
    platforms: Optional[List[str]] = None,
    caption_variants: Optional[List[str]] = None
) -> int:
    conn = get_connection()
    try:
        active_b = brand_id or (get_active_brand() or {}).get("id", 1)
        plats_json = json.dumps(platforms or ["INSTAGRAM"])
        vars_json = json.dumps(caption_variants or [caption])
        
        try:
            cur = conn.execute(
                """INSERT INTO drafts (image_url, caption, tone, media_type, brand_id, platforms, caption_variants, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')""",
                (image_url, caption, tone, media_type, active_b, plats_json, vars_json)
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.OperationalError:
            cur = conn.execute(
                """INSERT INTO drafts (image_url, caption, tone, media_type, status)
                   VALUES (?, ?, ?, ?, 'PENDING')""",
                (image_url, caption, tone, media_type)
            )
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

def get_draft(draft_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def delete_draft(draft_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def update_draft_caption(draft_id: int, new_caption: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("UPDATE drafts SET caption = ? WHERE id = ?", (new_caption, draft_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def get_pending_drafts(brand_id: Optional[int] = None) -> List[Tuple]:
    conn = get_connection()
    try:
        if brand_id:
            rows = conn.execute(
                "SELECT id, image_url, caption, tone, media_type, created_at FROM drafts WHERE status = 'PENDING' AND brand_id = ? ORDER BY id DESC",
                (brand_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, image_url, caption, tone, media_type, created_at FROM drafts WHERE status = 'PENDING' ORDER BY id DESC"
            ).fetchall()
        return [tuple(r) for r in rows]
    finally:
        conn.close()

# ============================================================
# STATS & HISTORY REPOSITORY
# ============================================================

def get_storage_stats() -> Dict[str, Any]:
    path = get_db_path()
    size_kb = round(os.path.getsize(path) / 1024, 1) if os.path.exists(path) else 0
    conn = get_connection()
    try:
        def _cnt(table: str) -> int:
            if table not in ALLOWED_TABLES:
                raise ValueError(f"Table '{table}' is not in allowed query whitelist.")
            try:
                return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                return 0
                
        return {
            "size_kb": size_kb,
            "posts": _cnt("posts"),
            "drafts": _cnt("drafts"),
            "analytics_cache": _cnt("analytics_cache"),
            "ai_calls": _cnt("ai_calls"),
            "brands": _cnt("brands"),
            "scheduled": _cnt("scheduled_posts")
        }
    finally:
        conn.close()

def get_post_history(limit: int = 10, brand_id: Optional[int] = None) -> List[Tuple]:
    conn = get_connection()
    try:
        safe_limit = max(1, min(100, int(limit)))
        if brand_id:
            rows = conn.execute(
                "SELECT id, post_id, caption, media_type, provider, timestamp FROM posts WHERE brand_id = ? ORDER BY id DESC LIMIT ?",
                (brand_id, safe_limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, post_id, caption, media_type, provider, timestamp FROM posts ORDER BY id DESC LIMIT ?",
                (safe_limit,)
            ).fetchall()
        return [tuple(r) for r in rows]
    finally:
        conn.close()

# ============================================================
# DMS & SCHEDULING REPOSITORY
# ============================================================

def get_seen_dms(platform: str = "INSTAGRAM") -> List[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT conversation_id FROM seen_dms WHERE platform = ?", (platform,)).fetchall()
        return [r["conversation_id"] for r in rows]
    except Exception:
        return []
    finally:
        conn.close()

def mark_dm_seen(conversation_id: str, platform: str = "INSTAGRAM", brand_id: Optional[int] = None):
    conn = get_connection()
    try:
        active_b = brand_id or (get_active_brand() or {}).get("id", 1)
        if _is_pg_conn(conn):
            conn.execute(
                "INSERT INTO seen_dms (conversation_id, platform, brand_id) VALUES (%s, %s, %s) ON CONFLICT (conversation_id) DO NOTHING",
                (conversation_id, platform, active_b)
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO seen_dms (conversation_id, platform, brand_id) VALUES (?, ?, ?)",
                (conversation_id, platform, active_b)
            )
        conn.commit()
    except Exception:
        try:
            if _is_pg_conn(conn):
                conn.execute("INSERT INTO seen_dms (conversation_id) VALUES (%s) ON CONFLICT (conversation_id) DO NOTHING", (conversation_id,))
            else:
                conn.execute("INSERT OR IGNORE INTO seen_dms (conversation_id) VALUES (?)", (conversation_id,))
            conn.commit()
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
    finally:
        try:
            conn.close()
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")

def save_scheduled_post(
    image_url: str,
    scheduled_time: str,
    tone: str = "casual",
    media_type: str = "IMAGE",
    post_type: str = "FEED",
    caption: Optional[str] = None,
    brand_id: Optional[int] = None,
    user_tz: str = "UTC"
) -> int:
    conn = get_connection()
    try:
        active_b = brand_id or (get_active_brand() or {}).get("id", 1)
        norm_time = normalize_datetime_to_utc(scheduled_time)
        cur = conn.execute(
            """INSERT INTO scheduled_posts (image_url, scheduled_time, scheduled_time_utc, tone, media_type, post_type, caption, status, brand_id, user_timezone)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)""",
            (image_url, norm_time, norm_time, tone, media_type, post_type, caption, active_b, user_tz)
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.OperationalError:
        cur = conn.execute(
            """INSERT INTO scheduled_posts (image_url, scheduled_time, tone, media_type, post_type, caption, status)
               VALUES (?, ?, ?, ?, ?, ?, 'PENDING')""",
            (image_url, scheduled_time, tone, media_type, post_type, caption)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def get_due_posts() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute(
            "SELECT * FROM scheduled_posts WHERE status = 'PENDING' AND scheduled_time <= ?",
            (now_utc,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def update_scheduled_status(sched_id: int, status: str, post_id: Optional[str] = None, last_error: Optional[str] = None):
    conn = get_connection()
    try:
        safe_err = mask_secrets(last_error) if last_error else None
        conn.execute(
            "UPDATE scheduled_posts SET status = ?, post_id = ?, last_error = ? WHERE id = ?",
            (status, post_id, safe_err, sched_id)
        )
        conn.commit()
    finally:
        conn.close()

def list_scheduled(brand_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        if brand_id:
            rows = conn.execute("SELECT * FROM scheduled_posts WHERE brand_id = ? ORDER BY scheduled_time ASC", (brand_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM scheduled_posts ORDER BY scheduled_time ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def cancel_scheduled(sched_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.execute("UPDATE scheduled_posts SET status = 'CANCELLED' WHERE id = ?", (sched_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
