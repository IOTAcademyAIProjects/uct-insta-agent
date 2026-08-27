"""
Content Repurposing Engine: Transform Single Source Content Across Platforms
Hardened with Resilient JSON Extraction.
"""

import json
import logging
from typing import Dict, Any, Optional, List

from core.model_router import get_default_router
from core.security import extract_json_from_llm
from services.brand_service import BrandService

logger = logging.getLogger("clawagent.repurpose")

class RepurposeService:
    def __init__(self):
        self.router = get_default_router()
        self.brand_service = BrandService()

    def repurpose_article(self, long_form_text: str, brand_id: Optional[int] = None) -> Dict[str, Any]:
        """Transforms a long-form article or thought piece into multi-platform assets."""
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        brand_name = brand.get("name", "Brand") if brand else "Brand"

        system_prompt = (
            f"You are the senior repurposing and distribution director for {brand_name}.\n"
            "Take the user's source text and transform it into 4 distinct platform formats.\n\n"
            "OUTPUT FORMAT (STRICT JSON ONLY):\n"
            "{\n"
            "  \"twitter_thread\": [\"tweet 1...\", \"tweet 2...\", \"tweet 3...\"],\n"
            "  \"instagram_carousel_slides\": [\"Slide 1 Title: ...\", \"Slide 2: ...\", \"Slide 3: ...\"],\n"
            "  \"quote_card_text\": \"Single most impactful 1-sentence quote\",\n"
            "  \"short_video_script\": \"30-second speaking script for Reels/Shorts\"\n"
            "}"
        )

        user_prompt = f"Source Content to Repurpose:\n\n{long_form_text}"

        try:
            raw = self.router.generate_text(
                task_type="reasoning",
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=800
            )
            return extract_json_from_llm(raw)
        except Exception as e:
            logger.error(f"Repurposing failed: {e}")
            return {
                "error": str(e),
                "twitter_thread": [long_form_text[:250]],
                "instagram_carousel_slides": ["Slide 1: " + long_form_text[:100]],
                "quote_card_text": long_form_text[:80],
                "short_video_script": "Summary: " + long_form_text[:200]
            }
