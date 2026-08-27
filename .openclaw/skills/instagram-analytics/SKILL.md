# Instagram Analytics — Performance Reporting & Strategy

**Skill:** `instagram-analytics`
**Description:** Performance reporting with date filtering, content-type ranking, and strategic AI recommendations via AnalystAgent. Fallback to curated summary when LLM unavailable.
**Triggers:** "show my analytics", "how are my posts doing?", "/analytics", "last 7 days"

## Commands

```bash
~/post-analytics.sh "DAYS"
python cli.py analytics --days 7
python cli.py analytics --days 30
python cli.py db ai_stats   # provider health/cost
```

## Pipeline
`agents/analyst_agent.py:23 analyze_performance(days)` reads `posts` `db/repository.py:33`, calculates `total_posts, reach, likes, comments, saved` `agents/analyst_agent.py:52-56`, ranks by `media_type` `agents/analyst_agent.py:58-66` → `prompts/analytics.py:build_analytics_prompt` → `router.generate_text(task_type=reasoning)` `core/model_router.py:127`

## Telegram Quick Actions
`SPEC_SHEET.md:872-876`
```
Row1: [📊 Last 7 Days] [📊 Last 30 Days]
Row2: [📊 Custom Range] [🔍 Competitor Compare]
```

## Failure Mode
If LLM down → returns local stats only: `"No posts logged in the last X days"` `agents/analyst_agent.py:46` or curated ranking without AI summary.
