"""
Scheduler Service: Manage Scheduled Post Queue and Publishing Triggers
Hardened with Datetime Normalization and Retry Error Logging.
"""

import os
import time
import logging
from core.security import mask_secrets
from typing import List, Dict, Any, Optional

from datetime import datetime, timezone

from db.repository import (
    save_scheduled_post, get_due_posts, update_scheduled_status,
    list_scheduled, cancel_scheduled, normalize_datetime_to_utc,
    get_connection
)
from agents.publisher_agent import PublisherAgent
from agents.creator_agent import CreatorAgent

logger = logging.getLogger("clawagent.scheduler")

class SchedulerService:
    def __init__(self):
        self.publisher = PublisherAgent()
        self.creator = CreatorAgent()

    def schedule(
        self,
        image_url: str,
        scheduled_time_str: str,
        tone: str = "casual",
        media_type: str = "IMAGE",
        post_type: str = "FEED",
        caption: Optional[str] = None,
        brand_id: Optional[int] = None,
        user_tz: str = "UTC"
    ) -> int:
        norm_time = normalize_datetime_to_utc(scheduled_time_str)
        return save_scheduled_post(
            image_url=image_url,
            scheduled_time=norm_time,
            tone=tone,
            media_type=media_type,
            post_type=post_type,
            caption=caption,
            brand_id=brand_id,
            user_tz=user_tz
        )

    def list_queue(self, brand_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return list_scheduled(brand_id)

    def cancel(self, post_id: int) -> bool:
        return cancel_scheduled(post_id)

    def get_last_weekly_brief(self, brand_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Returns most recent weekly brief ideas to implement cache (24h / same year-week)."""
        conn = get_connection()
        try:
            b_id = brand_id or 1
            now = datetime.now(timezone.utc)
            year, week, _ = now.isocalendar()
            year_week = year * 100 + week
            rows = conn.execute(
                "SELECT * FROM content_ideas WHERE brand_id=? AND week_number=? ORDER BY id DESC LIMIT 5",
                (b_id, year_week)
            ).fetchall()
            if rows:
                return {"week_number": year_week, "ideas": [dict(r) for r in rows], "cached": True}
            # Fallback to analytics_cache if used
            try:
                r = conn.execute("SELECT summary FROM analytics_cache WHERE brand_id=? ORDER BY id DESC LIMIT 1", (b_id,)).fetchone()
                if r:
                    return {"cached": False, "legacy": r["summary"]}
            except Exception as e:
                    logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
            return None
        finally:
            conn.close()

    def should_generate_weekly_brief(self, brand_id: Optional[int] = None) -> bool:
        """True if no brief for current ISO week exists (idempotent Mon 09:00)."""
        cached = self.get_last_weekly_brief(brand_id)
        return not (cached and cached.get("cached"))

    def generate_weekly_brief_if_needed(self, brand_id: Optional[int] = None, force: bool = False) -> Dict[str, Any]:
        """Implements S1.4 cache logic: generate only once per week unless force."""
        if not force and not self.should_generate_weekly_brief(brand_id):
            cached = self.get_last_weekly_brief(brand_id)
            return {"cached": True, "week_number": cached["week_number"], "ideas": cached["ideas"], "brief": "Cached brief for this week (use --force to regenerate)"}
        from agents.research_agent import ResearchAgent
        ra = ResearchAgent()
        brief_text = ra.generate_weekly_brief(brand_id=brand_id)
        # After generation, fetch fresh ideas
        fresh = self.get_last_weekly_brief(brand_id)
        return {"cached": False, "brief": brief_text, "ideas": fresh["ideas"] if fresh else []}

    def trigger_self_improve(self, brand_id: Optional[int] = None, dry_run: bool = True) -> Dict[str, Any]:
        """Weekly self-improvement propose — Monday 10am beat, 1 per week cap."""
        from services.self_improvement_service import SelfImprovementService
        svc = SelfImprovementService()
        return svc.propose(brand_id=brand_id or 1, dry_run=dry_run)

    def measure_self_improve(self, proposal_id: Optional[int] = None, brand_id: Optional[int] = None) -> Dict[str, Any]:
        """Sunday measure for last APPLIED proposal."""
        from services.self_improvement_service import SelfImprovementService
        svc = SelfImprovementService()
        if proposal_id:
            return svc.measure(proposal_id)
        # Measure most recent APPLIED
        hist = svc.get_history(brand_id=brand_id or 1, limit=5)
        for h in hist:
            if h["status"] == "APPLIED":
                return svc.measure(h["id"])
        return {"measured": 0, "reason": "No APPLIED proposal to measure"}

    def process_due_posts(self) -> List[Dict[str, Any]]:
        """Processes all pending scheduled posts that have reached execution time."""
        due = get_due_posts()
        results = []
        for post in due:
            sched_id = post["id"]
            img_url = post["image_url"]
            caption = post.get("caption")
            
            if not caption:
                try:
                    caption = self.creator.generate_caption(
                        description="Scheduled post image",
                        tone=post.get("tone", "casual"),
                        brand_id=post.get("brand_id", 1)
                    )
                except Exception as e:
                    logger.error(f"Failed to generate caption for scheduled post {sched_id}: {e}")
                    caption = "✨ Check out our latest update!"

            try:
                res = self.publisher.publish(
                    media_urls=[img_url],
                    caption=caption,
                    media_type=post.get("media_type", "IMAGE"),
                    post_type=post.get("post_type", "FEED"),
                    brand_id=post.get("brand_id", 1)
                )

                # Consider any platform success as overall success (H-05 fix)
                successes = [r for r in res.values() if getattr(r, 'success', False)]
                if successes:
                    first_ok = successes[0]
                    update_scheduled_status(sched_id, "POSTED", post_id=getattr(first_ok, 'post_id', None))
                    results.append({"sched_id": sched_id, "success": True, "post_id": getattr(first_ok, 'post_id', None), "results": {k: getattr(v,'success',False) for k,v in res.items()}})
                else:
                    errs = "; ".join([f"{k}:{getattr(v,'error','failed')}" for k,v in res.items()]) if res else "Unknown publish error"
                    update_scheduled_status(sched_id, "FAILED", last_error=errs)
                    results.append({"sched_id": sched_id, "success": False, "error": errs})
            except Exception as ex:
                update_scheduled_status(sched_id, "FAILED", last_error=str(ex))
                results.append({"sched_id": sched_id, "success": False, "error": str(ex)})

        return results
