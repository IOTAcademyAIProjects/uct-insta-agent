"""
Base Interface and Data Contracts for Social Media Platform Adapters
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class MediaSpec:
    aspect_ratios: List[str] = field(default_factory=lambda: ["1:1"])
    max_file_size_mb: float = 8.0
    supported_formats: List[str] = field(default_factory=lambda: ["jpg", "jpeg", "png", "mp4"])
    max_caption_length: int = 2200
    max_hashtags: int = 30
    recommended_hashtags: int = 5
    max_carousel_items: int = 10

@dataclass
class PublishResult:
    platform: str
    success: bool
    post_id: Optional[str] = None
    permalink: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

class PlatformAdapter(ABC):
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def get_media_spec(self, post_type: str = "FEED") -> MediaSpec:
        """Returns constraints for this post format."""
        pass

    @abstractmethod
    def format_caption(self, raw_caption: str, brand_context: Optional[Dict[str, Any]] = None) -> str:
        """Adapts caption text for platform-specific character limits and hashtag norms."""
        pass

    @abstractmethod
    def publish(
        self,
        media_urls: List[str],
        caption: str,
        media_type: str = "IMAGE",
        post_type: str = "FEED",
        brand_id: Optional[int] = None
    ) -> PublishResult:
        """Publishes single, carousel, or story media to the platform."""
        pass

    @abstractmethod
    def get_analytics(self, date_range: tuple, limit: int = 50) -> Dict[str, Any]:
        """Fetches post performance and engagement metrics."""
        pass
