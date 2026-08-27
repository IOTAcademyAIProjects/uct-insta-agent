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
    safe_stream_download, SecurityException, mask_secrets
)

logger = logging.getLogger("clawagent.media_host")

class MediaHostService:
    def __init__(self):
        self.imgbb_api_key = os.getenv("IMGBB_API_KEY")
        self.media_provider = os.getenv("MEDIA_PROVIDER", "imgbb").lower()  # imgbb|cloudinary|s3|direct
        self.cloudinary_url = os.getenv("CLOUDINARY_URL")

    def upload_from_url(self, image_url: str) -> str:
        """
        Downloads an image from a validated safe URL and rehosts per MEDIA_PROVIDER.
        Protected against SSRF and OOM attacks.
        Supports: imgbb (default unlimited free), cloudinary (if CLOUDINARY_URL), direct (no rehost).
        """
        safe_url = validate_safe_url(image_url)
        provider = self.media_provider
        # Direct mode or no key → return safe URL without rehost (saves quota)
        if provider == "direct":
            return safe_url
        if provider == "cloudinary" and self.cloudinary_url:
            try:
                image_bytes = safe_stream_download(image_url, max_bytes=20 * 1024 * 1024)
                return self.upload_to_cloudinary(image_bytes)
            except SecurityException as se:
                logger.error(f"Security block during URL media download: {se}")
                raise
            except Exception as e:
                logger.warning(f"Cloudinary rehost failed, fallback to direct: {e}")
                return safe_url
        # Default imgbb path
        if not self.imgbb_api_key:
            return safe_url

        try:
            image_bytes = safe_stream_download(image_url, max_bytes=20 * 1024 * 1024)
            return self.upload_from_bytes(image_bytes)
        except SecurityException as se:
            logger.error(f"Security block during URL media download: {se}")
            raise
        except Exception as e:
            logger.warning(f"Failed to rehost URL {image_url} to ImgBB: {e}. Validating URL...")
            return safe_url

    def upload_to_cloudinary(self, image_bytes: bytes) -> str:
        """Uploads to Cloudinary if configured (25K transforms free)."""
        if len(image_bytes) > 25 * 1024 * 1024:
            raise SecurityException("Payload size exceeds maximum allowed limit of 25MB.")
        try:
            import cloudinary
            import cloudinary.uploader
            # cloudinary.config from CLOUDINARY_URL env auto
            res = cloudinary.uploader.upload(image_bytes, resource_type="image")
            url = res.get("secure_url") or res.get("url")
            if not url:
                raise ValueError(f"Cloudinary did not return URL: {res}")
            return url
        except ImportError:
            raise ValueError("cloudinary not installed — pip install cloudinary or set MEDIA_PROVIDER=imgbb")
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {mask_secrets(str(e))}")
            raise

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

        # Size check before full read to prevent OOM
        size = os.path.getsize(safe_path)
        if size > 25 * 1024 * 1024:
            raise SecurityException(f"File too large: {size} bytes exceeds 25MB limit")

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
                # HEAD without following redirects to private IP — validate Location if redirect
                head = requests.head(safe_url, timeout=5, allow_redirects=False)
                if head.status_code in (301, 302, 303, 307, 308):
                    loc = head.headers.get("Location")
                    if loc:
                        try:
                            next_url = urllib.parse.urljoin(safe_url, loc)
                            validate_safe_url(next_url)
                            # Re-HEAD validated redirect target (one hop)
                            head = requests.head(next_url, timeout=5, allow_redirects=False)
                        except SecurityException:
                            return "IMAGE"  # Treat redirect to private IP as IMAGE (safe fallback)
                    else:
                        return "IMAGE"
                ctype = head.headers.get("Content-Type", "").lower()
                if "video" in ctype:
                    return "VIDEO"
            except Exception as e:
                    logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
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
