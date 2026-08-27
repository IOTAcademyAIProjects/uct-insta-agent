#!/usr/bin/env python3
"""
Phase 4: Celery beat crontab validation
"""
import unittest, sys, os
PROJECT_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

class TestCeleryBeat(unittest.TestCase):
    def test_celery_beat_uses_crontab(self):
        # Ensure celery_app beat_schedule uses crontab not fixed interval for weekly
        import importlib
        # Need REDIS_URL to enable celery
        os.environ["REDIS_URL"]="redis://localhost:6379/0"
        # Force reload
        if "celery_app" in sys.modules:
            del sys.modules["celery_app"]
        import celery_app
        import importlib as imp
        imp.reload(celery_app)
        self.assertTrue(celery_app.CELERY_ENABLED)
        self.assertIsNotNone(celery_app.celery_app)
        beat=celery_app.celery_app.conf.beat_schedule
        self.assertIn("weekly-brief-monday-9am", beat)
        self.assertIn("self-improve-propose-monday-10am", beat)
        # Check that schedule is crontab, not int
        from celery.schedules import crontab
        self.assertIsInstance(beat["weekly-brief-monday-9am"]["schedule"], crontab)
        self.assertIsInstance(beat["self-improve-propose-monday-10am"]["schedule"], crontab)
        # Verify crontab values: Mon 09:00 and Mon 10:00
        w=beat["weekly-brief-monday-9am"]["schedule"]
        self.assertEqual(w.hour, {9})
        self.assertEqual(w.day_of_week, {1})
        # Cleanup
        os.environ.pop("REDIS_URL", None)
        if "celery_app" in sys.modules:
            del sys.modules["celery_app"]

    def test_process_due_posts_still_exists(self):
        os.environ["REDIS_URL"]="redis://localhost:6379/0"
        if "celery_app" in sys.modules:
            del sys.modules["celery_app"]
        import celery_app
        import importlib
        importlib.reload(celery_app)
        self.assertIn("process-due-posts-every-minute", celery_app.celery_app.conf.beat_schedule)
        self.assertEqual(celery_app.celery_app.conf.beat_schedule["process-due-posts-every-minute"]["schedule"], 60.0)
        os.environ.pop("REDIS_URL", None)
        if "celery_app" in sys.modules:
            del sys.modules["celery_app"]

if __name__=='__main__':
    unittest.main()
