#!/usr/bin/env python3
"""
Tests for SelfImprovementService L1 loop
"""
import unittest, sys, os
PROJECT_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from db.setup_db import setup_database
from db.repository import get_connection
from services.self_improvement_service import SelfImprovementService
from services.brand_service import BrandService

class TestSelfImprove(unittest.TestCase):
    def setUp(self):
        setup_database()
        conn=get_connection()
        try:
            conn.execute("PRAGMA foreign_keys=OFF")
        except Exception:
            pass
        conn.execute("DELETE FROM improvement_log")
        conn.execute("DELETE FROM posts")
        # Seed brand
        conn.execute("INSERT OR IGNORE INTO brands (id, name, is_active, tone_of_voice, hashtag_count_range, sample_hooks) VALUES (1,'TestBrand',1,'casual','5-7','[]')")
        # Seed posts with varying engagement for observe
        for i, (cap, eng) in enumerate([("Hook A test",5.0),("Hook B test",1.0),("Hook C test",4.5)]):
            conn.execute("INSERT INTO posts (brand_id, caption, engagement_rate, likes, comments, platform) VALUES (1,?, ?, 10, 2, 'INSTAGRAM')",(cap, eng))
        conn.commit()
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        finally:
            conn.close()
        self.svc=SelfImprovementService()

    def test_observe(self):
        obs=self.svc.observe(brand_id=1)
        self.assertIn("top_posts", obs)
        self.assertIn("brand", obs)
        self.assertIn("top_hashtags_avg", obs)

    def test_propose_and_block_duplicate_week(self):
        res1=self.svc.propose(brand_id=1, dry_run=True)
        self.assertTrue(res1["proposed"])
        pid=res1["proposal"]["id"]
        # Second propose same week should be blocked
        res2=self.svc.propose(brand_id=1, dry_run=True)
        self.assertFalse(res2["proposed"])
        self.assertIn("already exists", res2["reason"].lower())
        # Cleanup
        self.svc.reject(pid)

    def test_approve_and_measure(self):
        res=self.svc.propose(brand_id=1, dry_run=True)
        pid=res["proposal"]["id"]
        # Approve L1 field should succeed
        field=res["proposal"]["changed_field"]
        if field in ("hashtag_count_range","sample_hooks","avg_sentence_length","emoji_frequency"):
            appr=self.svc.approve(pid)
            self.assertTrue(appr["success"])
            # Measure should keep or revert
            meas=self.svc.measure(pid)
            self.assertTrue(meas["success"])
            self.assertIn(meas["action"], ["KEEP","REVERTED"])
        else:
            self.svc.reject(pid)

    def test_reject(self):
        res=self.svc.propose(brand_id=1, dry_run=True)
        pid=res["proposal"]["id"]
        rej=self.svc.reject(pid)
        self.assertTrue(rej["success"])
        # Verify status
        history=self.svc.get_history(brand_id=1, limit=5)
        found=[h for h in history if h["id"]==pid]
        self.assertEqual(found[0]["status"], "REJECTED")

    def test_L3_gated_rejected(self):
        # Directly insert L3 proposal and try approve should fail
        conn=get_connection()
        conn.execute("INSERT INTO improvement_log (brand_id, week_number, experiment_type, hypothesis, changed_field, old_value, new_value, metric_before, predicted_lift, status) VALUES (1, 999999, 'L3_TONE','test','tone_of_voice','casual','formal',1.0,0.1,'PROPOSED')")
        conn.commit()
        pid=conn.execute("SELECT id FROM improvement_log WHERE week_number=999999").fetchone()["id"]
        conn.close()
        res=self.svc.approve(pid)
        self.assertFalse(res["success"])
        self.assertIn("L3", res["error"])
        # Cleanup
        conn=get_connection()
        try:
            conn.execute("PRAGMA foreign_keys=OFF")
        except Exception:
            pass
        conn.execute("DELETE FROM improvement_log WHERE id=?", (pid,))
        conn.commit()
        conn.close()

if __name__=='__main__':
    unittest.main()
