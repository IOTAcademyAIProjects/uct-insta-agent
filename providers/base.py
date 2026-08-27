"""
Abstract Base Provider Client Interface for ClawAgent
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

class ProviderClient(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config

    @property
    def provider_name(self) -> str:
        return self.name

    @property
    def supports_vision(self) -> bool:
        caps = self.config.get("capabilities", [])
        return "vision" in caps

    @property
    def supports_image_gen(self) -> bool:
        caps = self.config.get("capabilities", [])
        return "image_generation" in caps

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 400,
        temperature: float = 0.7
    ) -> str:
        """Generate text from a prompt."""
        pass

    def describe_image(
        self,
        image_url: str,
        prompt: Optional[str] = None,
        max_tokens: int = 150
    ) -> str:
        """Describe an image if supported by this provider."""
        raise NotImplementedError(f"Provider {self.name} does not support vision capabilities.")

    def generate_image(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1080,
        model: Optional[str] = None
    ) -> bytes:
        """Generate image bytes from a text prompt if supported."""
        raise NotImplementedError(f"Provider {self.name} does not support image generation.")
