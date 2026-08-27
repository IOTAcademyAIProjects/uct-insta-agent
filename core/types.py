"""
TypedDict definitions for enterprise strict typing — Phase 2
Covers Brand, Post, Draft, Proposal, Trend, Competitor etc.
"""

from typing import TypedDict, Optional, List, Literal, Any

class Brand(TypedDict, total=False):
    id: int
    name: str
    is_active: int
    color_palette: str
    typography_style: str
    visual_mood: str
    logo_url: Optional[str]
    tone_of_voice: str
    avg_sentence_length: float
    emoji_frequency: float
    emoji_style: str
    hashtag_count_range: str
    prohibited_words: str
    mandatory_elements: str
    sample_hooks: str
    instagram_user_id: Optional[str]
    linkedin_urn: Optional[str]
    twitter_handle: Optional[str]
    youtube_channel_id: Optional[str]
    composio_account_id: Optional[str]
    created_at: str
    updated_at: str

class Post(TypedDict, total=False):
    id: int
    campaign_id: Optional[int]
    brand_id: int
    platform: Literal["INSTAGRAM","LINKEDIN","TWITTER","YOUTUBE","FACEBOOK"]
    post_type: str
    caption: Optional[str]
    alt_text: Optional[str]
    media_urls: Optional[str]
    media_format: str
    caption_provider: Optional[str]
    vision_provider: Optional[str]
    image_gen_provider: Optional[str]
    brand_compliance_score: float
    post_id: Optional[str]
    media_type: str
    tone: str
    image_url: Optional[str]
    provider: Optional[str]
    status: str
    scheduled_time: Optional[str]
    posted_at: Optional[str]
    reach: int
    impressions: int
    likes: int
    comments: int
    shares: int
    saved: int
    engagement_rate: float

class Draft(TypedDict, total=False):
    id: int
    brand_id: int
    caption_variants: str
    selected_variant: int
    image_url: str
    caption: str
    tone: str
    platforms: str
    media_type: str
    status: str
    created_at: str

class TrendInsight(TypedDict, total=False):
    id: int
    brand_id: int
    topic: str
    relevance_score: float
    source: str
    trend_velocity: str
    suggested_content: str
    expires_at: Optional[str]
    created_at: str

class Competitor(TypedDict, total=False):
    id: int
    brand_id: int
    platform: str
    handle: str
    follower_count: int
    avg_engagement_rate: float
    last_scraped_at: Optional[str]

class ImprovementProposal(TypedDict, total=False):
    id: int
    brand_id: int
    week_number: int
    experiment_type: str
    hypothesis: str
    changed_field: str
    old_value: str
    new_value: str
    metric_before: float
    metric_after: Optional[float]
    predicted_lift: float
    status: Literal["PROPOSED","APPLIED","REJECTED","MEASURED","REVERTED"]
    dry_run: int
    created_at: str
    applied_at: Optional[str]
    measured_at: Optional[str]

class PublishResultTyped(TypedDict, total=False):
    platform: str
    success: bool
    post_id: Optional[str]
    permalink: Optional[str]
    error: Optional[str]

PlatformLiteral = Literal["INSTAGRAM","LINKEDIN","TWITTER","YOUTUBE"]
PostTypeLiteral = Literal["FEED","REEL","STORY","CAROUSEL","THREAD","SHORT","ARTICLE"]
StatusLiteral = Literal["PENDING","POSTED","FAILED","CANCELLED","REJECTED","APPROVED"]
