"""
Performance Memory — A/B Winner Learning Loop
Updates brand memory from engagement data after 48h
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from db.repository import get_connection
from services.brand_service import BrandService

logger = logging.getLogger("clawagent.performance")

class PerformanceMemory:
    def __init__(self):
        self.brand_service = BrandService()

    def rank_posts_by_engagement(self, brand_id: int = 1, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            # Prefer engagement_rate if present, else likes+comments
            rows = conn.execute("""
                SELECT * FROM posts WHERE brand_id=? AND (timestamp >= ? OR created_at >= ?)
                ORDER BY engagement_rate DESC, likes DESC, id DESC LIMIT ?
            """, (brand_id, cutoff, cutoff, limit)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Rank query failed: {e}")
            return []
        finally:
            conn.close()

    def update_brand_hooks_from_winners(self, brand_id: int = 1) -> Dict[str, Any]:
        """
        Identifies top 20% posts by engagement_rate and updates brands.sample_hooks
        to bias future CreatorAgent captions PRD.md:349-360
        Should be called 48h after posting via Scheduler beat.
        """
        posts = self.rank_posts_by_engagement(brand_id, days=30, limit=50)
        if len(posts) < 3:
            return {"updated": False, "reason": "Need ≥3 posts for learning"}

        # Top 20%
        top_n = max(1, len(posts) // 5)
        winners = posts[:top_n]
        # Extract hooks = first line per winner caption
        hooks = []
        for p in winners:
            cap = (p.get("caption") or "").strip()
            if not cap:
                continue
            first_line = cap.split("\n")[0].strip()[:80]
            if len(first_line) > 10 and not first_line.startswith("#"):
                hooks.append(first_line)

        if not hooks:
            return {"updated": False, "reason": "No hooks extracted"}

        # Merge with existing sample_hooks, keep max 10
        brand = self.brand_service.get_by_id(brand_id)
        existing_raw = brand.get("sample_hooks", "[]") if brand else "[]"
        try:
            existing = json.loads(existing_raw) if isinstance(existing_raw, str) else existing_raw
        except Exception:
            existing = []
        if not isinstance(existing, list):
            existing = []
        # Merge winners first, then existing, dedup
        merged = []
        seen = set()
        for h in hooks + existing:
            if h.lower() not in seen:
                seen.add(h.lower())
                merged.append(h)
        merged = merged[:10]

        # Persist via BrandService
        self.brand_service.update_profile(brand_id, {"sample_hooks": json.dumps(merged)})
        # Also update avg_sentence_length etc via analyze_brand_voice for full DNA refresh
        try:
            self.brand_service.analyze_brand_voice(brand_id)
        except Exception as e:
            logger.info(f"Brand voice refresh after win learning skipped: {e}")

        return {"updated": True, "winners": len(winners), "hooks": merged[:5], "total_posts": len(posts)}

    def get_ab_results(self, brand_id: int = 1, days: int = 14) -> List[Dict[str, Any]]:
        """Returns recent posts with variant grouping for A/B analysis display."""
        conn = get_connection()
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            rows = conn.execute("""
                SELECT id, caption, engagement_rate, likes, comments, platform, media_type, created_at
                FROM posts WHERE brand_id=? AND (timestamp >= ? OR created_at >= ?)
                ORDER BY engagement_rate DESC LIMIT 20
            """, (brand_id, cutoff, cutoff)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
