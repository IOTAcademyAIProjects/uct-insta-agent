"""
Google GenAI (Gemini) Provider Client for Text and Vision
Hardened with Safety Block Protections and Image RGB Normalization.
"""

import os
from io import BytesIO
from typing import Optional, Dict, Any
from providers.base import ProviderClient
from core.security import safe_stream_download

class GoogleGenAIProvider(ProviderClient):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.api_key_env = config.get("api_key_env", "GEMINI_API_KEY")
        self.api_key = os.getenv(self.api_key_env, "")
        self.model_name = config.get("model", "gemini-2.5-flash")
        self._configured = False

    def _ensure_configured(self):
        if not self.api_key:
            raise ValueError(f"Missing API key for Gemini in environment variable {self.api_key_env}")
        if not self._configured:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._configured = True

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 400,
        temperature: float = 0.7
    ) -> str:
        self._ensure_configured()
        import google.generativeai as genai

        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt if system_prompt else None
        )
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        response = model.generate_content(prompt, generation_config=generation_config)
        
        # Check safety filter blocks before reading .text
        if not response.candidates:
            raise ValueError("Gemini returned empty candidate list (possible prompt policy rejection).")
            
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        # finish_reason == 2 or 3 typically indicates SAFETY or RECITATION block
        if finish_reason in (2, 3, "SAFETY", "RECITATION"):
            raise ValueError(f"Gemini response blocked by safety filter: {finish_reason}")

        try:
            return response.text.strip()
        except ValueError as ve:
            # Fallback extraction from parts if .text property errors
            if candidate.content and candidate.content.parts:
                return candidate.content.parts[0].text.strip()
            raise ve

    def describe_image(
        self,
        image_url: str,
        prompt: Optional[str] = None,
        max_tokens: int = 150
    ) -> str:
        self._ensure_configured()
        import google.generativeai as genai
        from PIL import Image

        text_prompt = prompt or "Describe this image in 1-2 concise sentences for a social media caption."
        
        # Download image safely with size limits
        image_bytes = safe_stream_download(image_url, max_bytes=15 * 1024 * 1024)
        raw_img = Image.open(BytesIO(image_bytes))
        
        # Convert RGBA/CMYK/Palette images to standard RGB for Gemini
        if raw_img.mode != "RGB":
            img = raw_img.convert("RGB")
        else:
            img = raw_img

        model = genai.GenerativeModel(model_name=self.model_name)
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens
        )
        response = model.generate_content([text_prompt, img], generation_config=generation_config)
        
        if not response.candidates:
            raise ValueError("Gemini vision analysis returned empty candidates.")
            
        return response.text.strip()
