#!/usr/bin/env python3
"""
Phase 3: Media host coverage — SSRF redirect, size guard, HEAD validation
"""
import unittest, sys, os
from unittest.mock import patch, MagicMock
PROJECT_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from services.media_host import MediaHostService
from core.security import SecurityException, validate_safe_file_path
import tempfile

class TestMediaHost(unittest.TestCase):
    def test_upload_from_file_size_guard(self):
        svc=MediaHostService()
        # Create a temp file >25MB should be rejected before read (we mock getsize)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
            tf.write(b"x"*100)
            path=tf.name
        try:
            with patch("services.media_host.os.path.getsize", return_value=26*1024*1024):
                with self.assertRaises(SecurityException):
                    svc.upload_from_file(path, allowed_dirs=[os.path.dirname(path)])
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    def test_upload_from_file_traversal_blocked(self):
        svc=MediaHostService()
        with self.assertRaises(SecurityException):
            svc.upload_from_file("../../etc/passwd")

    def test_detect_media_type_ignores_query(self):
        svc=MediaHostService()
        self.assertEqual(svc.detect_media_type("https://images.example.com/cat.jpg?v=123&format=mp4"), "IMAGE")
        self.assertEqual(svc.detect_media_type("https://cdn.example.com/video.mp4?autoplay=1"), "VIDEO")

    def test_safe_stream_download_redirect_blocked(self):
        # Simulate redirect to private IP should be blocked via safe_stream_download
        from core.security import safe_stream_download
        # Mock requests.get to return 302 with Location to private IP
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.headers = {"Location": "http://10.0.0.1/secret"}
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: False
        with patch("core.security.validate_safe_url") as mock_validate:
            # First call passes, second call (redirect) should raise
            def side_effect(url, allowed_schemes=("http","https")):
                if "10.0.0.1" in url:
                    raise SecurityException("private IP")
                return url
            mock_validate.side_effect = side_effect
            with patch("requests.get", return_value=mock_resp):
                with self.assertRaises(SecurityException):
                    safe_stream_download("https://example.com/redirect", max_bytes=1024)

    def test_validate_safe_file_path_default_root(self):
        # No allowed_base_dirs should default to PROJECT_ROOT and block outside
        with self.assertRaises(SecurityException):
            validate_safe_file_path("C:\\Windows\\System32\\drivers\\etc\\hosts")
        # Project file should pass
        p=validate_safe_file_path("services/brand_service.py")
        self.assertTrue(p.endswith("brand_service.py"))

if __name__=='__main__':
    unittest.main()
