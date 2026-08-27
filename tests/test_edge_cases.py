#!/usr/bin/env python3
"""
Automated Edge-Case and Failure-Mode Unit Tests for ClawAgent
"""

import sys
import os
import time
import unittest
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.circuit_breaker import CircuitBreaker, CircuitState
from core.security import extract_json_from_llm
from db.repository import (
    get_connection, normalize_datetime_to_utc,
    save_scheduled_post, get_storage_stats
)
from services.media_host import MediaHostService
from services.brand_service import BrandService
from providers.pollinations import PollinationsProvider
from adapters.instagram import InstagramAdapter

class TestEdgeCases(unittest.TestCase):

    # 1. Circuit Breaker Probe Locking (DBG-01)
    def test_circuit_breaker_single_probe_lock(self):
        cb = CircuitBreaker("test_provider", failure_threshold=2, recovery_timeout_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # First request should be allowed as probe and set state to HALF_OPEN
        self.assertTrue(cb.allow_request())
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        
        # Subsequent requests while probe is in flight MUST be blocked
        self.assertFalse(cb.allow_request())
        
        # Probe succeeds -> closes circuit
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.allow_request())

    # 2. Resilient JSON Extractor (DBG-04)
    def test_json_extractor_with_preamble_and_fence(self):
        raw = "Certainly! Here is the classification:\n```json\n{\"intent\": \"ANALYTICS\", \"params\": {\"days\": 30}}\n```\nHope that helps!"
        res = extract_json_from_llm(raw)
        self.assertEqual(res["intent"], "ANALYTICS")
        self.assertEqual(res["params"]["days"], 30)

    def test_json_extractor_with_trailing_commas(self):
        raw = "{\"twitter_thread\": [\"tweet 1\", \"tweet 2\",], \"quote_card_text\": \"Inspiring quote\",}"
        res = extract_json_from_llm(raw)
        self.assertEqual(len(res["twitter_thread"]), 2)
        self.assertEqual(res["quote_card_text"], "Inspiring quote")

    # 3. Database Concurrency & WAL (DBG-03)
    def test_sqlite_concurrent_multithreading(self):
        errors = []
        def _worker(worker_id):
            try:
                conn = get_connection()
                for i in range(5):
                    conn.execute("SELECT COUNT(*) FROM brands")
                conn.close()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent DB access produced errors: {errors}")

    # 4. Media Detection with Query Parameters (DBG-10)
    def test_media_type_ignores_query_params(self):
        mhs = MediaHostService()
        self.assertEqual(mhs.detect_media_type("https://images.example.com/cat.jpg?v=123&format=mp4"), "IMAGE")
        self.assertEqual(mhs.detect_media_type("https://cdn.example.com/video.mp4?autoplay=1"), "VIDEO")
        self.assertEqual(mhs.detect_media_type("local_photo.PNG"), "IMAGE")
        self.assertEqual(mhs.detect_media_type("reel_recording.MOV"), "VIDEO")

    # 5. Datetime Normalization (DBG-09)
    def test_datetime_normalizer(self):
        self.assertEqual(normalize_datetime_to_utc("2026-08-27T10:00:00"), "2026-08-27 10:00:00")
        self.assertEqual(normalize_datetime_to_utc("2026-08-27 10:00"), "2026-08-27 10:00:00")
        self.assertEqual(normalize_datetime_to_utc("2026/08/27 10:00:00"), "2026-08-27 10:00:00")

    # 6. Brand Service NULL & Empty Guards (DBG-08)
    def test_brand_service_null_compliance(self):
        bs = BrandService()
        # Should not raise exception on NULL prohibited_words
        ok, issues = bs.check_compliance("Normal caption with positive vibes")
        self.assertTrue(ok)
        self.assertEqual(len(issues), 0)

    def test_brand_voice_empty_history(self):
        bs = BrandService()
        # Should return safe defaults instead of dividing by zero
        stats = bs.analyze_brand_voice(brand_id=99999)
        self.assertIn("avg_sentence_length", stats)
        self.assertGreater(stats["avg_sentence_length"], 0)

    # 7. Pollinations Image Magic Bytes (DBG-07)
    def test_pollinations_magic_bytes_check(self):
        p = PollinationsProvider()
        # Valid PNG
        self.assertTrue(p._is_valid_image_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"))
        # Valid JPEG
        self.assertTrue(p._is_valid_image_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"))
        # Valid WebP
        self.assertTrue(p._is_valid_image_bytes(b"RIFF\x00\x00\x00\x00WEBPVP8 "))
        # HTML error page
        self.assertFalse(p._is_valid_image_bytes(b"<!DOCTYPE html><html><body>Error 503</body></html>"))

    # 8. Instagram Response Error Validation (DBG-02)
    def test_instagram_response_validation(self):
        ig = InstagramAdapter()
        
        # Meta API error inside data
        error_resp = {
            "successful": False,
            "error": {"message": "Invalid OAuth access token.", "code": 190}
        }
        ok, cid, err = ig._validate_action_response(error_resp, "CREATE_POST")
        self.assertFalse(ok)
        self.assertIsNone(cid)
        self.assertIn("Invalid OAuth access token", err)

        # Successful creation response
        success_resp = {
            "data": {"id": "17987654321098765"}
        }
        ok, post_id, err = ig._validate_action_response(success_resp, "CREATE_POST")
        self.assertTrue(ok)
        self.assertEqual(post_id, "17987654321098765")
        self.assertIsNone(err)

if __name__ == '__main__':
    unittest.main()
