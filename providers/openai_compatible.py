"""
OpenAI-Compatible Provider Client (NVIDIA NIM, Cerebras, Mistral, OpenAI, OpenRouter, Ollama)
Hardened against Null Content & Empty Response Returns.
"""

import os
from typing import Optional, Dict, Any
from providers.base import ProviderClient

class OpenAICompatibleProvider(ProviderClient):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.base_url = config.get("base_url")
        self.api_key_env = config.get("api_key_env", "")
        self.api_key = os.getenv(self.api_key_env, "")
        self.model = config.get("model", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            api_key = self.api_key or "local-key"
            self._client = OpenAI(base_url=self.base_url, api_key=api_key)
        return self._client

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 400,
        temperature: float = 0.7
    ) -> str:
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if not response.choices:
            raise ValueError(f"Provider {self.name} returned zero choices.")

        content = response.choices[0].message.content
        if content is None:
            raise ValueError(f"Provider {self.name} returned null content (possible moderation filter).")
            
        clean_content = content.strip()
        if not clean_content:
            raise ValueError(f"Provider {self.name} returned empty string response.")
            
        return clean_content

    def describe_image(
        self,
        image_url: str,
        prompt: Optional[str] = None,
        max_tokens: int = 150
    ) -> str:
        client = self._get_client()
        text_prompt = prompt or "Describe this image in 1-2 concise sentences for a social media caption."
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ]
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens
        )
        
        if not response.choices:
            raise ValueError(f"Vision provider {self.name} returned zero choices.")
            
        content = response.choices[0].message.content
        if content is None:
            raise ValueError(f"Vision provider {self.name} returned null content.")
            
        return content.strip()
