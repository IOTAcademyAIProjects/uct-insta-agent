"""
Banana.dev Provider for Image Generation (Optional Paid Upgrade)
"""

import os
import requests
import base64
from typing import Optional, Dict, Any
from providers.base import ProviderClient

class BananaProvider(ProviderClient):
    def __init__(self, name: str = "banana_dev", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config or {})
        self.api_key_env = (config or {}).get("api_key_env", "BANANA_API_KEY")
        self.api_key = os.getenv(self.api_key_env, "")
        self.model = (config or {}).get("model", "flux-1-dev")
        self.base_url = (config or {}).get("base_url", "https://api.banana.dev/v1")

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 400,
        temperature: float = 0.7
    ) -> str:
        raise NotImplementedError("BananaProvider is configured for image generation.")

    def generate_image(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1080,
        model: Optional[str] = None
    ) -> bytes:
        if not self.api_key:
            raise ValueError(f"Missing Banana API Key in {self.api_key_env}")
        
        payload = {
            "apiKey": self.api_key,
            "modelKey": self.model,
            "modelInputs": {"prompt": prompt, "width": width, "height": height}
        }
        resp = requests.post(f"{self.base_url}/run", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        # Parse base64 image from result
        img_b64 = data.get("modelOutputs", [{}])[0].get("image_base64", "")
        if not img_b64:
            raise ValueError("No image output returned from Banana.dev")
        return base64.b64decode(img_b64)
