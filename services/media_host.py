"""
Unified Media Hosting & Transformation Service (ImgBB / Cloudinary / Local)
Hardened with SSRF, Path Traversal, Streaming Size Limit, and URL Path Normalization.
"""

import os
import requests
import base64
import logging
import urllib.parse
from typing import Optional

from core.security import (
    validate_safe_url, validate_safe_file_path,
    safe_stream_download, SecurityException
)

logger = logging.getLogger("clawagent.media_host")

class MediaHostService:
    def __init__(self):
        self.imgbb_api_key = os.getenv("IMGBB_API_KEY")

    def upload_from_url(self, image_url: str) -> str:
        """
        Downloads an image from a validated safe URL and rehosts on ImgBB.
        Protected against SSRF and OOM attacks.
        """
        if not self.imgbb_api_key:
            return validate_safe_url(image_url)

        try:
            image_bytes = safe_stream_download(image_url, max_bytes=20 * 1024 * 1024)
            return self.upload_from_bytes(image_bytes)
        except SecurityException as se:
            logger.error(f"Security block during URL media download: {se}")
            raise
        except Exception as e:
            logger.warning(f"Failed to rehost URL {image_url} to ImgBB: {e}. Validating URL...")
            return validate_safe_url(image_url)

    def upload_from_bytes(self, image_bytes: bytes) -> str:
        """Uploads raw image bytes to ImgBB."""
        if not self.imgbb_api_key:
            raise ValueError("IMGBB_API_KEY environment variable is required to upload image bytes.")

        if len(image_bytes) > 25 * 1024 * 1024:
            raise SecurityException("Payload size exceeds maximum allowed limit of 25MB.")

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "key": self.imgbb_api_key,
            "image": b64_image
        }
        res = requests.post("https://api.imgbb.com/1/upload", data=payload, timeout=30)
        res.raise_for_status()
        data = res.json()
        
        direct_url = data.get("data", {}).get("url")
        if not direct_url:
            raise ValueError(f"ImgBB did not return a valid direct URL: {data}")
        return direct_url

    def upload_from_file(self, file_path: str, allowed_dirs: Optional[list] = None) -> str:
        safe_path = validate_safe_file_path(file_path, allowed_base_dirs=allowed_dirs)
        if not os.path.exists(safe_path):
            raise FileNotFoundError(f"File not found: {safe_path}")

        with open(safe_path, "rb") as f:
            content = f.read()
        return self.upload_from_bytes(content)

    def detect_media_type(self, file_or_url: str) -> str:
        """
        Detects whether a file or URL points to VIDEO or IMAGE.
        Normalizes URL paths by stripping query parameters before checking extension.
        """
        if not file_or_url:
            return "IMAGE"

        # If it's a URL, extract path component cleanly without query parameters
        if file_or_url.startswith("http://") or file_or_url.startswith("https://"):
            try:
                parsed = urllib.parse.urlparse(file_or_url)
                path_only = parsed.path.lower()
                if path_only.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                    return "VIDEO"

                safe_url = validate_safe_url(file_or_url)
                head = requests.head(safe_url, timeout=5, allow_redirects=True)
                ctype = head.headers.get("Content-Type", "").lower()
                if "video" in ctype:
                    return "VIDEO"
            except Exception:
                pass
        else:
            clean_path = file_or_url.lower()
            if clean_path.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                return "VIDEO"

        return "IMAGE"

# Global helper instance
_media_host = MediaHostService()

def upload_to_imgbb(image_source) -> str:
    if isinstance(image_source, bytes):
        return _media_host.upload_from_bytes(image_source)
    elif isinstance(image_source, str):
        if os.path.exists(image_source):
            return _media_host.upload_from_file(image_source)
        elif image_source.startswith("http"):
            return _media_host.upload_from_url(image_source)
    raise ValueError(f"Unsupported image source: {type(image_source)}")
