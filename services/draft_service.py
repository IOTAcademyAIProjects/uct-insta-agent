"""
Draft Management Service with Brand Voice & A/B Caption Variants
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple

from core.model_router import get_default_router
from services.brand_service import BrandService
from db.repository import (
    save_draft, get_draft, delete_draft, update_draft_caption,
    get_pending_drafts, log_post
)
from prompts.caption import build_caption_prompt

logger = logging.getLogger("clawagent.draft")

class DraftService:
    def __init__(self):
        self.router = get_default_router()
        self.brand_service = BrandService()

    def create(
        self,
        image_url: str,
        tone: str = "casual",
        description: Optional[str] = None,
        brand_id: Optional[int] = None,
        platforms: Optional[List[str]] = None,
        media_type: str = "IMAGE",
        generate_variants: bool = True
    ) -> Dict[str, Any]:
        """Creates a pending draft post with brand voice calibration and A/B caption options."""
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        target_platforms = platforms or ["INSTAGRAM"]

        # If description is not supplied, use vision to describe the image
        img_desc = description
        if not img_desc:
            try:
                img_desc = self.router.describe_image(image_url)
            except Exception as e:
                logger.warning(f"Vision description failed, using fallback: {e}")
                img_desc = "A visual post for our audience"

        # Generate primary caption with brand context
        sys_prompt, user_prompt = build_caption_prompt(
            description=img_desc,
            tone=tone,
            platform=target_platforms[0],
            brand_context=brand,
            media_type=media_type
        )
        
        primary_caption = self.router.generate_text(
            task_type="creative_writing",
            prompt=user_prompt,
            system_prompt=sys_prompt,
            max_tokens=350
        )

        variants = [primary_caption]
        if generate_variants:
            # Generate 1 alternative variant with higher creativity
            try:
                var2_prompt = user_prompt + "\n\nProvide an alternative short, punchy hook angle."
                var2 = self.router.generate_text(
                    task_type="creative_writing",
                    prompt=var2_prompt,
                    system_prompt=sys_prompt,
                    max_tokens=300,
                    temperature=0.85
                )
                variants.append(var2)
            except Exception:
                pass

        draft_id = save_draft(
            image_url=image_url,
            caption=primary_caption,
            tone=tone,
            media_type=media_type,
            brand_id=brand.get("id", 1),
            platforms=target_platforms,
            caption_variants=variants
        )

        return {
            "draft_id": draft_id,
            "image_url": image_url,
            "caption": primary_caption,
            "caption_variants": variants,
            "tone": tone,
            "media_type": media_type,
            "platforms": target_platforms,
            "brand_name": brand.get("name", "DefaultBrand"),
            "description": img_desc
        }

    def get(self, draft_id: int) -> Optional[Dict[str, Any]]:
        return get_draft(draft_id)

    def update_caption(self, draft_id: int, new_caption: str) -> bool:
        return update_draft_caption(draft_id, new_caption)

    def reject(self, draft_id: int) -> bool:
        return delete_draft(draft_id)

    def list_pending(self, brand_id: Optional[int] = None) -> List[Tuple]:
        return get_pending_drafts(brand_id)

    def approve(self, draft_id: int) -> Dict[str, Any]:
        """Approves and publishes the draft via the Publisher Agent / Platform Adapter."""
        draft = get_draft(draft_id)
        if not draft:
            return {"success": False, "error": f"Draft {draft_id} not found"}

        from agents.publisher_agent import PublisherAgent
        publisher = PublisherAgent()
        
        platforms_raw = draft.get("platforms", '["INSTAGRAM"]')
        try:
            target_platforms = json.loads(platforms_raw) if isinstance(platforms_raw, str) else platforms_raw
        except Exception:
            target_platforms = ["INSTAGRAM"]

        results = publisher.publish(
            media_urls=[draft["image_url"]],
            caption=draft["caption"],
            media_type=draft.get("media_type", "IMAGE"),
            platforms=target_platforms,
            brand_id=draft.get("brand_id", 1)
        )

        # Delete draft once published
        delete_draft(draft_id)
        return {
            "success": True,
            "draft_id": draft_id,
            "results": results
        }
