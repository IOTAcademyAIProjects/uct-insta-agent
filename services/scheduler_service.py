"""
Scheduler Service: Manage Scheduled Post Queue and Publishing Triggers
Hardened with Datetime Normalization and Retry Error Logging.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional

from db.repository import (
    save_scheduled_post, get_due_posts, update_scheduled_status,
    list_scheduled, cancel_scheduled, normalize_datetime_to_utc
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

                ig_res = res.get("INSTAGRAM")
                if ig_res and ig_res.success:
                    update_scheduled_status(sched_id, "POSTED", post_id=ig_res.post_id)
                    results.append({"sched_id": sched_id, "success": True, "post_id": ig_res.post_id})
                else:
                    err = ig_res.error if ig_res else "Unknown publish error"
                    update_scheduled_status(sched_id, "FAILED", last_error=err)
                    results.append({"sched_id": sched_id, "success": False, "error": err})
            except Exception as ex:
                update_scheduled_status(sched_id, "FAILED", last_error=str(ex))
                results.append({"sched_id": sched_id, "success": False, "error": str(ex)})

        return results
