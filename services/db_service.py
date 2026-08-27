"""
Database Inspection & Maintenance Service
"""

import sys
import os
import sqlite3
from typing import Dict, Any, List

from db.repository import (
    get_storage_stats, get_post_history, get_pending_drafts,
    delete_draft, get_db_path, get_connection
)

class DBService:
    def __init__(self):
        pass

    def get_stats(self) -> Dict[str, Any]:
        return get_storage_stats()

    def get_history(self, limit: int = 10) -> List[Any]:
        return get_post_history(limit)

    def get_drafts(self) -> List[Any]:
        return get_pending_drafts()

    def delete_draft(self, draft_id: int) -> bool:
        return delete_draft(draft_id)

    def get_ai_stats(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT provider, COUNT(*) as calls,
                          SUM(success) as successful,
                          AVG(latency_ms) as avg_latency
                   FROM ai_calls GROUP BY provider"""
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []
        finally:
            conn.close()

    def clear_drafts(self) -> int:
        conn = get_connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]
            conn.execute("DELETE FROM drafts")
            conn.commit()
            return count
        finally:
            conn.close()

    def clear_history(self) -> int:
        conn = get_connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            conn.execute("DELETE FROM posts")
            conn.commit()
            return count
        finally:
            conn.close()
