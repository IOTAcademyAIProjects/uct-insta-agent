"""
Designer Agent: AI Image Generation with Brand Aesthetic Calibration
"""

import logging
from typing import Optional, Dict, Any

from core.model_router import get_default_router
from services.brand_service import BrandService
from services.media_host import MediaHostService

logger = logging.getLogger("clawagent.designer")

class DesignerAgent:
    def __init__(self):
        self.router = get_default_router()
        self.brand_service = BrandService()
        self.media_host = MediaHostService()

    def generate_image(
        self,
        prompt: str,
        brand_id: Optional[int] = None,
        width: int = 1080,
        height: int = 1080
    ) -> Dict[str, Any]:
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        
        # Inject brand visual mood into image prompt
        enhanced_prompt = prompt
        if brand:
            mood = brand.get("visual_mood", "")
            palette = brand.get("color_palette", "")
            if mood:
                enhanced_prompt += f", {mood} aesthetic"
        
        # Route to image generation provider (Pollinations -> Banana -> Replicate)
        img_bytes = self.router.generate_image(
            prompt=enhanced_prompt,
            width=width,
            height=height
        )

        # Upload image to ImgBB to obtain public direct URL
        direct_url = self.media_host.upload_from_bytes(img_bytes)

        return {
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "image_url": direct_url,
            "width": width,
            "height": height
        }
