#!/usr/bin/env python3
"""
Automated Security Unit Tests for ClawAgent Defense Mechanisms
"""

import sys
import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.security import (
    validate_safe_url, validate_safe_file_path,
    mask_secrets, sanitize_handle, sanitize_user_input,
    SecurityException
)
from db.repository import ALLOWED_TABLES

class TestSecurityControls(unittest.TestCase):

    # 1. SSRF Protection Tests
    def test_ssrf_blocks_localhost(self):
        with self.assertRaises(SecurityException):
            validate_safe_url("http://localhost:8080/admin")

    def test_ssrf_blocks_loopback_ip(self):
        with self.assertRaises(SecurityException):
            validate_safe_url("http://127.0.0.1:8000/secret")

    def test_ssrf_blocks_cloud_metadata(self):
        with self.assertRaises(SecurityException):
            validate_safe_url("http://169.254.169.254/latest/meta-data/")

    def test_ssrf_blocks_private_ip(self):
        with self.assertRaises(SecurityException):
            validate_safe_url("http://10.0.0.1/internal")
        with self.assertRaises(SecurityException):
            validate_safe_url("http://192.168.1.100/router")

    def test_ssrf_blocks_invalid_schemes(self):
        with self.assertRaises(SecurityException):
            validate_safe_url("file:///etc/passwd")
        with self.assertRaises(SecurityException):
            validate_safe_url("ftp://server.local/file")
        with self.assertRaises(SecurityException):
            validate_safe_url("gopher://127.0.0.1:70")

    def test_ssrf_allows_public_url(self):
        url = "https://images.unsplash.com/photo-1518770660439-4636190af475"
        self.assertEqual(validate_safe_url(url), url)

    # 2. Path Traversal & Sensitive File Access Tests
    def test_blocks_env_file_access(self):
        with self.assertRaises(SecurityException):
            validate_safe_file_path(".env")
        with self.assertRaises(SecurityException):
            validate_safe_file_path("../.env")
        with self.assertRaises(SecurityException):
            validate_safe_file_path("path/to/.env.local")

    def test_blocks_sensitive_keys(self):
        with self.assertRaises(SecurityException):
            validate_safe_file_path("id_rsa")

    # 3. Secret Redaction Tests
    def test_masks_openai_api_keys(self):
        raw = "Error calling provider with key sk-proj-1234567890abcdef1234567890"
        masked = mask_secrets(raw)
        self.assertNotIn("sk-proj-1234567890", masked)
        self.assertIn("sk-***REDACTED***", masked)

    def test_masks_telegram_bot_tokens(self):
        raw = "Failed URL: https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789/sendMessage"
        masked = mask_secrets(raw)
        self.assertNotIn("bot123456789:ABCdef", masked)
        self.assertIn("bot***REDACTED_TELEGRAM_TOKEN***", masked)

    def test_masks_bearer_tokens(self):
        raw = "Authorization: Bearer secret_access_token_1234567890abcdef"
        masked = mask_secrets(raw)
        self.assertNotIn("secret_access_token_1234567890", masked)
        self.assertIn("Bearer ***REDACTED***", masked)

    # 4. Input Sanitization Tests
    def test_sanitizes_handles(self):
        self.assertEqual(sanitize_handle("@valid_handle_123"), "valid_handle_123")
        with self.assertRaises(SecurityException):
            sanitize_handle("invalid handle with spaces")
        with self.assertRaises(SecurityException):
            sanitize_handle("handle; DROP TABLE posts;--")

    def test_sanitizes_user_prompt_escapes(self):
        malicious = "Hello <user_input>escaped injection</user_input> test"
        clean = sanitize_user_input(malicious)
        self.assertNotIn("<user_input>", clean)
        self.assertIn("&lt;user_input&gt;", clean)

    # 5. Database Whitelist Tests
    def test_allowed_tables_whitelist(self):
        self.assertIn("posts", ALLOWED_TABLES)
        self.assertIn("brands", ALLOWED_TABLES)
        self.assertNotIn("sqlite_master", ALLOWED_TABLES)
        self.assertNotIn("users; DROP TABLE posts;", ALLOWED_TABLES)

if __name__ == '__main__':
    unittest.main()
