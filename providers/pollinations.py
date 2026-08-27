"""
Pollinations AI Provider for Free Text-to-Image Generation
Hardened with Image Magic-Byte Verification and Strict Payload Validation.
"""

import time
import requests
import urllib.parse
from typing import Optional, Dict, Any
from providers.base import ProviderClient

class PollinationsProvider(ProviderClient):
    def __init__(self, name: str = "pollinations", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config or {})
        self.base_url = (config or {}).get("base_url", "https://image.pollinations.ai")
        self.default_model = (config or {}).get("model", "flux")

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 400,
        temperature: float = 0.7
    ) -> str:
        raise NotImplementedError("PollinationsProvider only supports image generation.")

    def _is_valid_image_bytes(self, data: bytes) -> bool:
        """Verifies binary header magic bytes for JPEG, PNG, GIF, or WebP."""
        if not data or len(data) < 4:
            return False
        # JPEG: FF D8 FF
        if data.startswith(b"\xff\xd8\xff"):
            return True
        # PNG: 89 50 4E 47
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return True
        # WebP: RIFF ... WEBP
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return True
        # GIF: GIF87a or GIF89a
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return True
        return False

    def generate_image(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1080,
        model: Optional[str] = None
    ) -> bytes:
        selected_model = model or self.default_model
        encoded_prompt = urllib.parse.quote(prompt.strip())
        seed = int(time.time() * 1000) % 1000000
        url = f"{self.base_url}/prompt/{encoded_prompt}?width={width}&height={height}&model={selected_model}&seed={seed}&nologo=true"
        
        headers = {
            "User-Agent": "ClawAgent/3.0 (Social Media AI Operating System)"
        }
        
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        
        if len(resp.content) < 1000:
            raise ValueError(f"Pollinations returned suspiciously small payload ({len(resp.content)} bytes).")
            
        if not self._is_valid_image_bytes(resp.content):
            # If payload is HTML or plaintext error message
            preview = resp.content[:200].decode("utf-8", errors="ignore")
            raise ValueError(f"Pollinations returned non-image format (possible rate limit or HTML error): {preview}")
            
        return resp.content
