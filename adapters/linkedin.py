"""
LinkedIn Platform Adapter via LinkedIn Marketing API v2
"""

import os
import requests
import logging
from typing import List, Optional, Dict, Any

from adapters.base import PlatformAdapter, MediaSpec, PublishResult
from db.repository import log_post

logger = logging.getLogger("clawagent.linkedin")

class LinkedInAdapter(PlatformAdapter):
    def __init__(self, name: str = "linkedin", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.author_urn = os.getenv("LINKEDIN_PERSON_URN") # urn:li:person:XXXX or urn:li:organization:XXXX

    def get_media_spec(self, post_type: str = "FEED") -> MediaSpec:
        return MediaSpec(
            aspect_ratios=["1:1", "1.91:1"],
            max_file_size_mb=10.0,
            supported_formats=["jpg", "jpeg", "png", "pdf"],
            max_caption_length=3000,
            max_hashtags=5,
            recommended_hashtags=3
        )

    def format_caption(self, raw_caption: str, brand_context: Optional[Dict[str, Any]] = None) -> str:
        # LinkedIn professional framing with concise hashtags
        return raw_caption[:3000]

    def publish(
        self,
        media_urls: List[str],
        caption: str,
        media_type: str = "IMAGE",
        post_type: str = "FEED",
        brand_id: Optional[int] = None
    ) -> PublishResult:
        if not self.access_token or not self.author_urn:
            return PublishResult(
                platform="LINKEDIN",
                success=False,
                error="LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN environment variable not configured."
            )

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        # Structure UGC Post payload
        payload = {
            "author": self.author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": self.format_caption(caption)
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        try:
            resp = requests.post(
                "https://api.linkedin.com/v2/ugcPosts",
                json=payload,
                headers=headers,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            post_urn = data.get("id")

            log_post(
                post_id=str(post_urn),
                caption=caption,
                media_type=media_type,
                tone="professional",
                image_url=media_urls[0] if media_urls else "",
                provider="LinkedIn_v2",
                brand_id=brand_id,
                platform="LINKEDIN"
            )

            return PublishResult(
                platform="LINKEDIN",
                success=True,
                post_id=str(post_urn),
                raw_response=data
            )
        except Exception as e:
            logger.error(f"LinkedIn publishing failed: {e}")
            return PublishResult(platform="LINKEDIN", success=False, error=str(e))

    def get_analytics(self, date_range: tuple, limit: int = 50) -> Dict[str, Any]:
        return {"platform": "LINKEDIN", "posts": []}
