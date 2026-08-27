"""
X / Twitter Platform Adapter via Twitter API v2
"""

import os
import requests
import logging
from typing import List, Optional, Dict, Any

from adapters.base import PlatformAdapter, MediaSpec, PublishResult
from db.repository import log_post

logger = logging.getLogger("clawagent.twitter")

class TwitterAdapter(PlatformAdapter):
    def __init__(self, name: str = "twitter", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_SECRET")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    def get_media_spec(self, post_type: str = "FEED") -> MediaSpec:
        return MediaSpec(
            aspect_ratios=["16:9", "1:1"],
            max_file_size_mb=5.0,
            supported_formats=["jpg", "jpeg", "png", "gif", "mp4"],
            max_caption_length=280,
            max_hashtags=2,
            recommended_hashtags=1
        )

    def format_caption(self, raw_caption: str, brand_context: Optional[Dict[str, Any]] = None) -> str:
        # X / Twitter limit: 280 characters
        if len(raw_caption) <= 280:
            return raw_caption
        return raw_caption[:277] + "..."

    def publish(
        self,
        media_urls: List[str],
        caption: str,
        media_type: str = "IMAGE",
        post_type: str = "FEED",
        brand_id: Optional[int] = None
    ) -> PublishResult:
        if not self.api_key or not self.access_token:
            return PublishResult(
                platform="TWITTER",
                success=False,
                error="TWITTER_API_KEY or TWITTER_ACCESS_TOKEN environment variable not configured."
            )

        formatted_text = self.format_caption(caption)
        try:
            from requests_oauthlib import OAuth1
            auth = OAuth1(self.api_key, self.api_secret, self.access_token, self.token_secret)
            
            payload = {"text": formatted_text}
            resp = requests.post("https://api.twitter.com/2/tweets", json=payload, auth=auth, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            tweet_id = data.get("data", {}).get("id")

            log_post(
                post_id=str(tweet_id),
                caption=formatted_text,
                media_type=media_type,
                tone="casual",
                image_url=media_urls[0] if media_urls else "",
                provider="Twitter_v2",
                brand_id=brand_id,
                platform="TWITTER"
            )

            return PublishResult(
                platform="TWITTER",
                success=True,
                post_id=str(tweet_id),
                permalink=f"https://x.com/i/web/status/{tweet_id}",
                raw_response=data
            )
        except Exception as e:
            logger.error(f"Twitter publish failed: {e}")
            return PublishResult(platform="TWITTER", success=False, error=str(e))

    def get_analytics(self, date_range: tuple, limit: int = 50) -> Dict[str, Any]:
        return {"platform": "TWITTER", "tweets": []}
