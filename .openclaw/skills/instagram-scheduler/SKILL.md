# Instagram Scheduler — Stories & Future Posts

**Skill:** `instagram-scheduler`
**Description:** Post immediate Instagram Stories or schedule future feed/story posts. Handles timezone normalization POST_TIMEZONE→UTC and due-post worker.
**Triggers:** "post to my story", "schedule this for tomorrow at 5 PM", "schedule queue"

## Commands

```bash
# Story now
~/post-story.sh "IMAGE_URL"
python pipelines/scheduler.py story "URL"

# Schedule future
~/scheduler.sh schedule "IMAGE_URL" "YYYY-MM-DD HH:MM" "casual"
python pipelines/scheduler.py schedule "URL" "2026-08-28 15:00" "casual"
python cli.py scheduler schedule "URL" "2026-08-28 15:00"  # via services/scheduler_service.py

# Manage queue
~/scheduler.sh list
python pipelines/scheduler.py list
python pipelines/scheduler.py run   # publish due
python pipelines/scheduler.py cancel 42
python pipelines/scheduler.py weekly-brief [--force]  # S1.4 Monday 09:00 beat

# Cron (server)
* * * * * bash /path/scheduler.sh run >> logs/cron.log 2>&1
0 9 * * 1 bash /path/scheduler.sh weekly-brief >> logs/brief.log 2>&1
```

## Pipeline
`flowchart.md:232-262`
- `schedule_post()` `pipelines/scheduler.py:123` + `services/scheduler_service.py:25 schedule()` → `normalize_datetime_to_utc()` `db/repository.py:46` → `save_scheduled_post()` `db/repository.py:365` `scheduled_posts` `db/setup_db.py:181` `status=PENDING`
- Worker `run_scheduler()` `pipelines/scheduler.py:272` / `SchedulerService.process_due_posts()` `services/scheduler_service.py:54` every 60s → `PublisherAgent.publish()` → `update_scheduled_status(POSTED/FAILED)` `db/repository.py:409`

## Timezone
`POST_TIMEZONE=Asia/Kolkata` `.env.example:55` → stored UTC, displayed local `pipelines/scheduler.py:202-208`

## S1.4 Weekly Brief Beat
`services/scheduler_service.py:generate_weekly_brief_if_needed()` idempotent per ISO week `content_ideas.week_number` `db/setup_db.py:147` + `pipelines/scheduler.py weekly-brief` cache.
