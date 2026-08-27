"""
Celery App — Optional Redis-backed queue for team deployment
Fallback to in-process when REDIS_URL not set or celery not installed.
SPEC_SHEET.md:926-973
"""

import os
import logging

logger = logging.getLogger("clawagent.celery")

REDIS_URL = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL")
CELERY_ENABLED = bool(REDIS_URL)

celery_app = None

if CELERY_ENABLED:
    try:
        from celery import Celery
        celery_app = Celery(
            "clawagent",
            broker=REDIS_URL,
            backend=REDIS_URL,
        )
        # Use crontab for weekly beats (enterprise), fallback to interval if crontab unavailable
        try:
            from celery.schedules import crontab
            weekly_brief_sched = crontab(hour=9, minute=0, day_of_week=1)  # Mon 09:00
            improve_propose_sched = crontab(hour=10, minute=0, day_of_week=1)  # Mon 10:00
            improve_measure_sched = crontab(hour=21, minute=0, day_of_week=0)  # Sun 21:00
        except ImportError:
            weekly_brief_sched = 60*60*24*7
            improve_propose_sched = 60*60*24*7
            improve_measure_sched = 60*60*24*7

        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone=os.getenv("POST_TIMEZONE", "UTC"),
            enable_utc=True,
            beat_schedule={
                "process-due-posts-every-minute": {
                    "task": "celery_app.process_due_posts",
                    "schedule": 60.0,
                },
                "weekly-brief-monday-9am": {
                    "task": "celery_app.weekly_brief",
                    "schedule": weekly_brief_sched,
                },
                "self-improve-propose-monday-10am": {
                    "task": "celery_app.self_improve_propose",
                    "schedule": improve_propose_sched,
                },
                "self-improve-measure-sunday-9pm": {
                    "task": "celery_app.self_improve_measure",
                    "schedule": improve_measure_sched,
                },
            },
        )

        @celery_app.task(name="celery_app.process_due_posts")
        def process_due_posts():
            from services.scheduler_service import SchedulerService
            svc = SchedulerService()
            results = svc.process_due_posts()
            return {"processed": len(results), "results": results}

        @celery_app.task(name="celery_app.weekly_brief")
        def weekly_brief(brand_id=None, force=False):
            from services.scheduler_service import SchedulerService
            svc = SchedulerService()
            return svc.generate_weekly_brief_if_needed(brand_id=brand_id, force=force)

        @celery_app.task(name="celery_app.sync_competitors")
        def sync_competitors(brand_id=None):
            from services.competitor_service import CompetitorService
            cs = CompetitorService()
            return cs.sync_competitor_posts(brand_id=brand_id)

        @celery_app.task(name="celery_app.self_improve_propose")
        def self_improve_propose(brand_id=None, dry_run=True):
            from services.self_improvement_service import SelfImprovementService
            svc = SelfImprovementService()
            return svc.propose(brand_id=brand_id or 1, dry_run=dry_run)

        @celery_app.task(name="celery_app.self_improve_measure")
        def self_improve_measure(proposal_id=None, brand_id=None):
            from services.self_improvement_service import SelfImprovementService
            svc = SelfImprovementService()
            if proposal_id:
                return svc.measure(proposal_id)
            # Measure most recent APPLIED for brand
            history = svc.get_history(brand_id=brand_id or 1, limit=5)
            for h in history:
                if h["status"] == "APPLIED":
                    return svc.measure(h["id"])
            return {"measured": 0}

        logger.info(f"Celery enabled with broker {REDIS_URL[:20]}...")
    except ImportError as e:
        logger.warning(f"REDIS_URL set but celery not installed: {e} — falling back to in-process")
        celery_app = None
        CELERY_ENABLED = False
    except Exception as e:
        logger.warning(f"Celery init failed: {e}")
        celery_app = None
        CELERY_ENABLED = False
else:
    logger.info("Celery disabled — using in-process APScheduler/SQLite queue (solo mode)")

def is_celery_enabled() -> bool:
    return CELERY_ENABLED and celery_app is not None
