"""
Replicate Provider for Image Generation (Optional Paid Upgrade)
"""

import os
import requests
from typing import Optional, Dict, Any
from providers.base import ProviderClient

class ReplicateProvider(ProviderClient):
    def __init__(self, name: str = "replicate", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config or {})
        self.api_key_env = (config or {}).get("api_key_env", "REPLICATE_API_TOKEN")
        self.api_token = os.getenv(self.api_key_env, "")
        self.model = (config or {}).get("model", "black-forest-labs/flux-schnell")

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 400,
        temperature: float = 0.7
    ) -> str:
        raise NotImplementedError("ReplicateProvider is configured for image generation.")

    def generate_image(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1080,
        model: Optional[str] = None
    ) -> bytes:
        if not self.api_token:
            raise ValueError(f"Missing Replicate API Token in {self.api_key_env}")
        
        import replicate
        output = replicate.run(
            self.model,
            input={
                "prompt": prompt,
                "aspect_ratio": "1:1",
                "output_format": "jpg"
            }
        )
        # Output is usually a list with image URL or FileOutput
        img_url = str(output[0]) if isinstance(output, list) else str(output)
        resp = requests.get(img_url, timeout=30)
        resp.raise_for_status()
        return resp.content
