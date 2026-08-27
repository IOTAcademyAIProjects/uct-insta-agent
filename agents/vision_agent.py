"""
Vision Agent: Image & Video Visual Description and Analysis
"""

import logging
from typing import Optional, List, Dict, Any
from core.model_router import get_default_router

logger = logging.getLogger("clawagent.vision")

class VisionAgent:
    def __init__(self):
        self.router = get_default_router()

    def describe_image(self, image_url: str, prompt: Optional[str] = None) -> str:
        """Extracts rich visual context and subject matter from an image URL."""
        custom_p = prompt or "Describe the key subject, colors, mood, and context of this image in 1-2 concise sentences for social media copywriting."
        return self.router.describe_image(image_url, prompt=custom_p)

    def extract_visual_elements(self, image_url: str) -> Dict[str, Any]:
        """Extracts structured visual characteristics for brand profile alignment."""
        prompt = (
            "Analyze this image and return a JSON object with keys: "
            "'dominant_colors' (list of 2-3 hex or color names), 'mood' (e.g. minimalist, energetic, cozy), "
            "'subject' (brief description)."
        )
        try:
            desc = self.router.describe_image(image_url, prompt=prompt)
            return {"raw_analysis": desc}
        except Exception as e:
            return {"error": str(e)}
