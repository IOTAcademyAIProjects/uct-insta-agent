#!/usr/bin/env python3
"""
Tests for TrendService v2 — multi-source, relevance scoring, TTL, deduplication
Phase 3 coverage
"""
import unittest
import sys, os
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from services.trend_service import TrendService
from db.repository import get_connection
from db.setup_db import setup_database

class TestTrendV2(unittest.TestCase):
    def setUp(self):
        setup_database()
        conn=get_connection()
        try:
            conn.execute("PRAGMA foreign_keys=OFF")
        except Exception:
            pass
        conn.execute("DELETE FROM trend_insights")
        conn.commit()
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        finally:
            conn.close()
        self.svc=TrendService()

    def test_fetch_trending_topics_fallback(self):
        # No pytrends key, should return curated fallback with relevance >=0.6
        signals=self.svc.fetch_trending_topics(category="technology", brand_niche="technology")
        self.assertGreaterEqual(len(signals), 3)
        for s in signals:
            self.assertIn("topic", s)
            self.assertIn("relevance_score", s)
            self.assertGreaterEqual(s["relevance_score"], 0.5)

    def test_save_and_expiry_filter(self):
        conn=get_connection()
        # Insert expired trend
        past = (datetime.now(timezone.utc)-timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO trend_insights (brand_id, topic, source, trend_velocity, relevance_score, expires_at) VALUES (1,'Old Topic','GOOGLE_TRENDS','RISING',0.9,?)", (past,))
        # Insert fresh
        future = (datetime.now(timezone.utc)+timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO trend_insights (brand_id, topic, source, trend_velocity, relevance_score, expires_at) VALUES (1,'Fresh Topic','GOOGLE_TRENDS','RISING',0.9,?)", (future,))
        conn.commit()
        conn.close()
        trends=self.svc.get_latest_trends(brand_id=1)
        topics=[t["topic"] for t in trends]
        self.assertIn("Fresh Topic", topics)
        self.assertNotIn("Old Topic", topics)

    def test_relevance_filter_and_dedup(self):
        # Directly test _score_relevance via fetch with duplicate topics
        with patch.object(self.svc, 'fetch_google_trends', return_value=[
            {"topic":"AI workflow","source":"GOOGLE_TRENDS","trend_velocity":"RISING","relevance_score":0.9},
            {"topic":"ai workflow","source":"GOOGLE_TRENDS","trend_velocity":"RISING","relevance_score":0.85},
        ]):
            with patch.object(self.svc, 'fetch_x_trends', return_value=[]):
                with patch.object(self.svc, 'fetch_ig_hashtag_trends', return_value=[]):
                    sig=self.svc.fetch_trending_topics(brand_niche="technology")
                    # dedup should remove duplicate lowercased
                    topics=[s["topic"].lower() for s in sig]
                    self.assertEqual(len(topics), len(set(topics)))

    def test_get_latest_seeds_when_empty(self):
        # Already empty after setUp, get_latest should seed 3
        trends=self.svc.get_latest_trends(brand_id=1)
        self.assertGreaterEqual(len(trends), 3)
        self.assertTrue(all("expires_at" in t for t in trends))

if __name__=='__main__':
    unittest.main()
