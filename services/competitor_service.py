"""
Competitor Intelligence Service: Track Competitor Handles & Gap Analysis
"""

import logging
from typing import List, Dict, Any, Optional
from db.repository import get_connection

logger = logging.getLogger("clawagent.competitor")

class CompetitorService:
    def __init__(self):
        pass

    def add_competitor(self, handle: str, platform: str = "INSTAGRAM", brand_id: Optional[int] = None) -> int:
        conn = get_connection()
        try:
            b_id = brand_id or 1
            clean_handle = handle.strip().lstrip("@")
            cur = conn.execute(
                """INSERT OR IGNORE INTO competitors (brand_id, platform, handle, follower_count, avg_engagement_rate)
                   VALUES (?, ?, ?, 0, 0.0)""",
                (b_id, platform.upper(), clean_handle)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def list_competitors(self, brand_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            b_id = brand_id or 1
            rows = conn.execute("SELECT * FROM competitors WHERE brand_id = ?", (b_id,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def log_competitor_post(
        self,
        competitor_id: int,
        post_type: str,
        caption_summary: str,
        est_engagement: float = 0.0
    ):
        conn = get_connection()
        try:
            conn.execute(
                """INSERT INTO competitor_posts (competitor_id, post_type, caption_summary, estimated_engagement)
                   VALUES (?, ?, ?, ?)""",
                (competitor_id, post_type, caption_summary, est_engagement)
            )
            conn.commit()
        finally:
            conn.close()
