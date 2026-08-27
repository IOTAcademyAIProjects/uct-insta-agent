"""
Publisher Agent: Multi-Platform Publishing Coordinator
"""

import os
import logging
from typing import List, Optional, Dict, Any

from adapters.base import PlatformAdapter, PublishResult
from adapters.instagram import InstagramAdapter
from adapters.linkedin import LinkedInAdapter
from adapters.twitter import TwitterAdapter
from adapters.youtube import YouTubeAdapter
from services.media_host import MediaHostService
from services.brand_service import BrandService

logger = logging.getLogger("clawagent.publisher")

class PublisherAgent:
    def __init__(self):
        self.adapters: Dict[str, PlatformAdapter] = {
            "INSTAGRAM": InstagramAdapter(),
            "LINKEDIN": LinkedInAdapter(),
            "TWITTER": TwitterAdapter(),
            "YOUTUBE": YouTubeAdapter()
        }
        self.media_host = MediaHostService()
        self.brand_service = BrandService()

    def get_adapter(self, platform_name: str) -> Optional[PlatformAdapter]:
        return self.adapters.get(platform_name.upper())

    def publish(
        self,
        media_urls: List[str],
        caption: str,
        media_type: str = "IMAGE",
        platforms: Optional[List[str]] = None,
        post_type: str = "FEED",
        brand_id: Optional[int] = None
    ) -> Dict[str, PublishResult]:
        """Publishes content across multiple selected social media platforms."""
        target_platforms = platforms or ["INSTAGRAM"]
        brand_ctx = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()

        # Ensure media URLs are hosted publicly (ImgBB)
        hosted_urls = []
        for url in media_urls:
            try:
                hosted_url = self.media_host.upload_from_url(url)
                hosted_urls.append(hosted_url)
            except Exception as e:
                logger.warning(f"Could not rehost {url}, using raw: {e}")
                hosted_urls.append(url)

        results: Dict[str, PublishResult] = {}
        for plat in target_platforms:
            plat_upper = plat.upper()
            adapter = self.get_adapter(plat_upper)
            if not adapter:
                results[plat_upper] = PublishResult(
                    platform=plat_upper,
                    success=False,
                    error=f"Platform '{plat_upper}' adapter is not supported or not loaded."
                )
                continue

            # Format caption specific to this platform
            formatted_cap = adapter.format_caption(caption, brand_context=brand_ctx)

            # Publish
            res = adapter.publish(
                media_urls=hosted_urls,
                caption=formatted_cap,
                media_type=media_type,
                post_type=post_type,
                brand_id=brand_ctx.get("id", 1) if brand_ctx else 1
            )
            results[plat_upper] = res

        return results
