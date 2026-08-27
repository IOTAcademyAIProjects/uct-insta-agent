"""
Creator Agent: Caption Writing, Variant Generation & Content Ideation
"""

import json
import logging
from core.security import mask_secrets
from typing import Dict, Any, Optional, List, Tuple

from core.model_router import get_default_router
from services.brand_service import BrandService
from prompts.caption import build_caption_prompt, build_carousel_prompt

logger = logging.getLogger("clawagent.creator")

class CreatorAgent:
    def __init__(self):
        self.router = get_default_router()
        self.brand_service = BrandService()

    def generate_caption(
        self,
        description: str,
        tone: str = "casual",
        platform: str = "INSTAGRAM",
        brand_id: Optional[int] = None,
        media_type: str = "IMAGE"
    ) -> str:
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        sys_p, user_p = build_caption_prompt(
            description=description,
            tone=tone,
            platform=platform,
            brand_context=brand,
            media_type=media_type
        )
        return self.router.generate_text(
            task_type="creative_writing",
            prompt=user_p,
            system_prompt=sys_p,
            max_tokens=350
        )

    def generate_caption_variants(
        self,
        description: str,
        tone: str = "casual",
        platform: str = "INSTAGRAM",
        brand_id: Optional[int] = None,
        count: int = 3
    ) -> List[str]:
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        sys_p, user_p = build_caption_prompt(
            description=description,
            tone=tone,
            platform=platform,
            brand_context=brand
        )
        
        variants = []
        # Primary
        v1 = self.router.generate_text("creative_writing", user_p, system_prompt=sys_p, max_tokens=300)
        variants.append(v1)
        
        if count > 1:
            try:
                # Variant 2: Short & punchy
                v2_prompt = user_p + "\n\nVariant 2 style: Ultra short, curiosity-driven punchy hook."
                v2 = self.router.generate_text("creative_writing", v2_prompt, system_prompt=sys_p, max_tokens=250, temperature=0.85)
                variants.append(v2)
            except Exception as e:
                    logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
                
        if count > 2:
            try:
                # Variant 3: Storyteller
                v3_prompt = user_p + "\n\nVariant 3 style: Narrative opener with deep engagement question."
                v3 = self.router.generate_text("creative_writing", v3_prompt, system_prompt=sys_p, max_tokens=350, temperature=0.9)
                variants.append(v3)
            except Exception as e:
                    logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
                
        return variants

    def generate_carousel_caption(self, slide_count: int, tone: str = "casual", brand_id: Optional[int] = None) -> str:
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        sys_p, user_p = build_carousel_prompt(slide_count, tone=tone, brand_context=brand)
        return self.router.generate_text("creative_writing", user_p, system_prompt=sys_p, max_tokens=350)
