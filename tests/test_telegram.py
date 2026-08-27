#!/usr/bin/env python3
"""
Tests for Telegram keyboards and callbacks HITL
"""
import unittest, sys, os
PROJECT_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ["ALLOW_OPEN"]="true"
from telegram.keyboards import build_draft_keyboard, build_brand_keyboard, build_analytics_keyboard, build_self_improve_keyboard, render_draft_preview_text, render_self_improve_text
from telegram.callbacks import handle_callback
from telegram.bot import is_allowed_user, handle_photo_message
from db.setup_db import setup_database
from db.repository import get_connection

class TestTelegram(unittest.TestCase):
    def test_draft_keyboard_structure(self):
        kb=build_draft_keyboard(47, has_variants=True)
        self.assertEqual(kb[0][0]["callback_data"], "approve:47")
        # Has Use A/B row when variants
        flat=[b["callback_data"] for row in kb for b in row]
        self.assertIn("use_a:47", flat)
        self.assertIn("use_b:47", flat)
        kb2=build_draft_keyboard(47, has_variants=False)
        flat2=[b["callback_data"] for row in kb2 for b in row]
        self.assertNotIn("use_a:47", flat2)

    def test_brand_keyboard(self):
        brands=[{"name":"BrandX"}, {"name":"ClientY"}]
        kb=build_brand_keyboard(brands, active_name="BrandX")
        texts=[b["text"] for row in kb for b in row]
        self.assertTrue(any("BrandX (active)" in t for t in texts))
        self.assertTrue(any("New Brand" in t for t in texts))

    def test_self_improve_keyboard(self):
        kb=build_self_improve_keyboard(12)
        flat=[b["callback_data"] for row in kb for b in row]
        self.assertIn("improve_apply:12", flat)
        self.assertIn("improve_reject:12", flat)

    def test_handle_callback_approve_not_found(self):
        res=handle_callback("approve:99999")
        self.assertIn("not found", res["text"].lower())

    def test_handle_callback_brand_switch(self):
        setup_database()
        from services.brand_service import BrandService
        from db.repository import get_connection
        bs=BrandService()
        # Ensure brand exists (handle duplicate from prior runs due to FK ON)
        try:
            bs.create("TestBrandTg", tone_of_voice="casual")
        except Exception:
            pass
        # Ensure it exists even if duplicate
        conn=get_connection()
        try:
            conn.execute("INSERT OR IGNORE INTO brands (name, is_active, tone_of_voice) VALUES ('TestBrandTg',0,'casual')")
            conn.commit()
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
        res=handle_callback("brand_switch:TestBrandTg")
        self.assertIn("switched", res["text"].lower())

    def test_handle_photo_message_blocked_private(self):
        res=handle_photo_message("http://10.0.0.1/secret.jpg", user_id="999")
        self.assertIn("blocked", res["text"].lower())

    def test_is_allowed_user(self):
        # Test allowlist without ALLOW_OPEN (fail-closed)
        orig_allow = os.environ.pop("ALLOW_OPEN", None)
        os.environ["TELEGRAM_ALLOW_FROM"]="111,222"
        self.assertTrue(is_allowed_user("111"))
        self.assertFalse(is_allowed_user("999"))
        os.environ.pop("TELEGRAM_ALLOW_FROM", None)
        # Test ALLOW_OPEN bypass
        os.environ["ALLOW_OPEN"]="true"
        self.assertTrue(is_allowed_user("999"))
        os.environ.pop("ALLOW_OPEN", None)
        if orig_allow is not None:
            os.environ["ALLOW_OPEN"] = orig_allow
        else:
            os.environ["ALLOW_OPEN"] = "true"

    def test_render_texts(self):
        draft={"id":1, "caption":"Test caption", "image_url":"https://example.com/a.jpg", "tone":"casual", "platforms":'["INSTAGRAM"]', "caption_variants":'["a","b"]'}
        txt=render_draft_preview_text(draft, brand_name="BrandX")
        self.assertIn("Draft Preview #1", txt)
        prop={"id":5, "changed_field":"hashtag_count_range","old_value":"5-7","new_value":"1-3","hypothesis":"test","predicted_lift":0.15,"status":"PROPOSED","week_number":202635,"experiment_type":"L1_HASHTAG","metric_before":3.5,"dry_run":1}
        txt2=render_self_improve_text(prop, brand_name="BrandX")
        self.assertIn("Proposal #5", txt2)

if __name__=='__main__':
    unittest.main()
