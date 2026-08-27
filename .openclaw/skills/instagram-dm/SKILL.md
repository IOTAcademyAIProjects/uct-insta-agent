# Instagram DM — Inbox & Comment Management

**Skill:** `instagram-dm`
**Description:** Direct message inbox and comment management via Composio + Telegram notifications + sentiment analysis.
**Triggers:** "check my DMs", "show comments on post 123", "/dms"

## Commands

```bash
~/dm-manager.sh dms
~/dm-manager.sh comments POST_ID
~/dm-manager.sh delete COMMENT_ID

python pipelines/dm-comments.py dms
python pipelines/dm-comments.py comments POST_ID
```

## Services
- `services/engagement_service.py:1` sentiment `POSITIVE/NEUTRAL/NEGATIVE`, `engagement_log` `db/setup_db.py` (analytics_cache equivalent `db/setup_db.py:211`)
- `seen_dms` dedup `db/setup_db.py:201-207` `db/repository.py:337-345`
- Telegram notify via `TELEGRAM_NOTIFY_CHAT_ID` `pipelines/scheduler.py:312-323`

## Security
`sanitize_user_input` for post_id, comment deletion requires allowlist.
