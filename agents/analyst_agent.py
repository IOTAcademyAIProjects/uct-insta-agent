"""
Analyst Agent: Social Media Performance Analytics & Growth Intelligence
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone

from core.model_router import get_default_router
from adapters.instagram import InstagramAdapter
from services.brand_service import BrandService
from prompts.analytics import build_analytics_prompt
from db.repository import get_connection

logger = logging.getLogger("clawagent.analyst")

class AnalystAgent:
    def __init__(self):
        self.router = get_default_router()
        self.ig_adapter = InstagramAdapter()
        self.brand_service = BrandService()

    def analyze_performance(self, days: int = 7, brand_id: Optional[int] = None) -> Dict[str, Any]:
        """Calculates engagement analytics and generates an AI summary."""
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        brand_name = brand.get("name", "Brand") if brand else "Brand"

        # Check local posts DB first
        conn = get_connection()
        try:
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            b_id = brand.get("id", 1) if brand else 1
            rows = conn.execute(
                "SELECT * FROM posts WHERE brand_id = ? AND timestamp >= ? ORDER BY id DESC",
                (b_id, cutoff)
            ).fetchall()
            posts = [dict(r) for r in rows]
        finally:
            conn.close()

        date_range_str = f"Last {days} days"
        total_posts = len(posts)
        
        if total_posts == 0:
            return {
                "summary": f"No posts logged in the last {days} days for {brand_name}. Start posting to see performance analytics!",
                "total_posts": 0,
                "posts": []
            }

        # Calculate metrics
        total_reach = sum(p.get("reach", 0) for p in posts)
        total_likes = sum(p.get("likes", 0) for p in posts)
        total_comments = sum(p.get("comments", 0) for p in posts)
        total_saved = sum(p.get("saved", 0) for p in posts)

        # Content type breakdown
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for p in posts:
            mtype = p.get("media_type", "IMAGE").upper()
            by_type.setdefault(mtype, []).append(p)

        type_stats = []
        for mtype, plist in by_type.items():
            avg_eng = sum(p.get("likes", 0) + p.get("comments", 0) for p in plist) / len(plist)
            type_stats.append(f"{mtype}: {len(plist)} posts, avg engagement = {round(avg_eng, 1)}")

        ranking_text = "\n".join(type_stats)
        data_text = f"Total Posts: {total_posts} | Total Reach: {total_reach} | Total Likes: {total_likes} | Total Comments: {total_comments} | Total Saved: {total_saved}"

        sys_p, user_p = build_analytics_prompt(
            data_text=data_text,
            ranking_text=ranking_text,
            date_range=date_range_str,
            brand_name=brand_name
        )

        ai_summary = self.router.generate_text(
            task_type="reasoning",
            prompt=user_p,
            system_prompt=sys_p,
            max_tokens=400
        )

        return {
            "summary": ai_summary,
            "total_posts": total_posts,
            "total_reach": total_reach,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "ranking": type_stats,
            "date_range": date_range_str
        }
