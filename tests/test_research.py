#!/usr/bin/env python3
"""
Tests for ResearchAgent v2 — weekly brief JSON + content_ideas persistence
"""
import unittest, sys, os, json
from unittest.mock import patch, MagicMock
PROJECT_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from db.setup_db import setup_database
from db.repository import get_connection
from agents.research_agent import ResearchAgent

class TestResearch(unittest.TestCase):
    def setUp(self):
        setup_database()
        conn=get_connection()
        try:
            conn.execute("PRAGMA foreign_keys=OFF")
        except Exception:
            pass
        conn.execute("DELETE FROM content_ideas")
        conn.execute("DELETE FROM trend_insights")
        conn.execute("DELETE FROM competitors")
        conn.execute("DELETE FROM competitor_posts")
        # Ensure brand exists
        conn.execute("INSERT OR IGNORE INTO brands (id, name, is_active, tone_of_voice) VALUES (1,'TestBrand',1,'casual')")
        conn.commit()
        # Seed trend
        from datetime import datetime, timezone, timedelta
        future=(datetime.now(timezone.utc)+timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO trend_insights (brand_id, topic, source, trend_velocity, relevance_score, expires_at) VALUES (1,'Test Trend','GOOGLE_TRENDS','RISING',0.9,?)",(future,))
        conn.commit()
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        finally:
            conn.close()
        self.ra=ResearchAgent()

    def test_weekly_brief_fallback_creates_ideas(self):
        # No LLM keys -> fallback should still create 5 ideas
        txt=self.ra.generate_weekly_brief(brand_id=1)
        self.assertIn("Weekly Content Intelligence", txt)
        conn=get_connection()
        cnt=conn.execute("SELECT COUNT(*) FROM content_ideas WHERE brand_id=1").fetchone()[0]
        conn.close()
        self.assertGreaterEqual(cnt, 5)

    def test_weekly_brief_persists_year_week(self):
        self.ra.generate_weekly_brief(brand_id=1)
        conn=get_connection()
        rows=conn.execute("SELECT week_number FROM content_ideas WHERE brand_id=1").fetchall()
        conn.close()
        # week_number should be year*100+week >= 202600
        for r in rows:
            self.assertGreater(r["week_number"], 202600)

    def test_competitor_brief_no_competitors(self):
        txt=self.ra.analyze_competitors(brand_id=1)
        self.assertIn("No competitor", txt)

    def test_competitor_brief_with_data(self):
        conn=get_connection()
        conn.execute("INSERT OR IGNORE INTO competitors (id, brand_id, platform, handle) VALUES (1,1,'INSTAGRAM','testcomp')")
        conn.execute("INSERT INTO competitor_posts (competitor_id, post_type, caption_summary, estimated_engagement) VALUES (1,'CAROUSEL','test summary',0.05)")
        conn.commit()
        conn.close()
        txt=self.ra.analyze_competitors(brand_id=1)
        # Should not be the empty message, should contain competitor handle or gap analysis
        self.assertNotIn("No competitor handles tracked yet", txt)

if __name__=='__main__':
    unittest.main()
