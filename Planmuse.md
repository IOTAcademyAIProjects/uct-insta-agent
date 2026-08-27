# Planmuse.md — ClawAgent v3.0 Execution Plan (SDLC Loop)

**Project:** ClawAgent — Multi-Agent Social Media Operating System  
**Version:** 3.0.0  
**Codename:** UTC_oc / OpenClaw Agent  
**Author:** Swarit Sharma / Uniconverge Technologies  
**Date:** 2026-08-27  
**Status:** Engineering Execution Blueprint — implement → test → debug → repeat  
**Source PRD:** `PRD.md:1-462` | **Spec:** `SPEC_SHEET.md:1-973` | **Architecture:** `flowchart.md:1-587`

> **How to use this file:** Follow streams `S1→S4` sequentially or in parallel as dependencies allow. Each task follows the **SDLC micro-loop**: `Design → Implement → Test → Debug → Review → Record`. No task is DONE until its **Verification Gate** passes. No weekly timeline — priority and dependencies drive order.

---

## 0. Ground Rules & SDLC Loop

### 0.1 Global Principles
- **Cost = ₹0 default.** Every feature must work on free-tier providers `config/models.yaml:15-96`. Paid keys (`banana_dev`, `replicate`, `openai` `config/models.yaml:97-135`) are `enabled:false` optional upgrades.
- **Specialize, don't generalize.** Orchestrator `agents/orchestrator.py:1` routes to cheapest/fastest model per `core/model_router.py:92-125`. Vision never wastes creative tokens.
- **Memory is non-negotiable.** Brand DNA `services/brand_service.py:76-150` injected into every `prompts/caption.py:1` generation.
- **Human-in-the-loop, not human-in-the-way.** Destructive publish requires approval `services/draft_service.py:113-142`; reads are instant.
- **Security first.** Every URL/path/input via `core/security.py:1` (`validate_safe_url`, `validate_safe_file_path`, `sanitize_user_input`, `mask_secrets`). Never log raw keys.

### 0.2 The Loop (apply to EVERY task)

```
[1 DESIGN]  → spec the interface, DB change, prompt, fallback
      ↓
[2 IMPLEMENT] → smallest vertical slice, feature-flagged
      ↓
[3 TEST]      → unit + integration + manual (see 0.4)
      ↓
[4 DEBUG]     → reproduce → isolate → fix → re-test
      ↓
[5 REVIEW]    → `git diff`, `git log --oneline -5`, self-review against Spec gate
      ↓
[6 RECORD]    → update `db/setup_db.py:DDL`, `README.md:CLI table`, `SPEC_SHEET.md` if contract changed
      ↻ loop until gate GREEN
```

**Parallelization rule:** Any two tasks with no shared file + no DB migration conflict may run in parallel via `Task` subagents. Shared files (`db/repository.py:1`, `core/model_router.py:1`, `config/models.yaml:1`) require sequential edit or `edit` with full context.

### 0.3 Branching & Hygiene
- Branch: `git checkout -b feat/<stream>-<slug>` from `main`.
- Commit prefix: `feat(S1):`, `fix(S2):`, `chore(S4):`. Never commit `.env`, `db/uct_agent.sqlite`, `logs/`.
- Before commit: `python tests/test_security.py` + `python tests/test_edge_cases.py` must pass `flowchart.md:564-570`.
- PR gate: `git status` clean, `git diff` covers intent, no secrets via `core/security.py:mask_secrets`.

### 0.4 Testing Pyramid (mandatory per stream)
- **Unit:** mock providers, assert fallbacks, circuit breaker transitions `core/circuit_breaker.py:1`.
- **Integration:** real SQLite WAL `db/repository.py:29-44`, `get_due_posts()` `db/repository.py:397-407`, `save_draft()` `db/repository.py:210-242`.
- **E2E/CLI:** `cli.py:45-393` commands with sanitized inputs.
- **Manual Telegram:** photo → preview card → approve → `posts.status=POSTED`.

### 0.5 Definition of DONE (per task)
- [ ] Code implements Spec contract exactly (`SPEC_SHEET.md:6`)
- [ ] Fallback/circuit breaker handled `core/model_router.py:134-183`
- [ ] Secrets masked, SSRF/path traversal guarded `core/security.py:1`
- [ ] Unit + integration tests GREEN, manual verified
- [ ] `cli.py` or Telegram path documented in `README.md:52-72` + `SKILLS.md:1-59`
- [ ] No regression: existing 24 tests (14 security + 10 edge) GREEN

### 0.6 Execution Order & Dependencies
```
S0 (Foundation) ─┬─► S1 Intelligence ◄─┐
                 ├─► S2 Telegram UX    ├─► S3 Advanced (needs S1+S2) ─► S4 Scale (needs S0)
                 └─► S0.2 Infra audit ─┘
```
- **Start now in parallel:** S1.1 prep + S2.1 manifests + S0.2 infra audit (no conflicts).
- **Sequential gates:** S1 brief needs S1.1+S1.2; S3 repurpose needs S1 trends + S2 draft cards; S4 Docker needs S0.2 DB abstraction design.

---

## S0 — Foundation Audit & Stabilization (Do First, 1 slice)

**Goal:** Freeze contracts, audit gaps, make repo loop-ready.

### S0.1 Repo Map Verification
- **Files to read:** `flowchart.md:316-412` codebase map, `config/models.yaml:1-154`, `config/platforms.yaml:1`, `.env.example:1-56`, `db/setup_db.py:19-310`, `core/exceptions.py:1`, `prompts/__init__.py:1`.
- **Tasks:**
  - [ ] Verify `idea` branch vs `main` drift: `git diff main --stat`.
  - [ ] Run `bash setup.sh` fresh, `python db/setup_db.py`, `python cli.py ai-status` `core/model_router.py:265-280` shows `circuit_state=CLOSED`, `has_credentials` per `config/models.yaml:15-96`.
  - [ ] Run `python cli.py db storage` `services/db_service.py:1` → `size_kb, posts, drafts, ai_calls` `db/repository.py:290-313`.
  - [ ] Run `python tests/test_security.py` + `python tests/test_edge_cases.py` record baseline failures.
- **SDLC Loop:** Design=n/a, Implement=fix missing columns via `db/setup_db.py:222-276 migrate_missing_columns`, Test=rerun, Debug=isolate WAL lock `db/repository.py:38-41`, Review=diff.

### S0.2 Contract Freeze
- **Design:** Lock interfaces per `SPEC_SHEET.md:88-633`:
  - `PlatformAdapter` `adapters/base.py:1` (`get_media_spec`, `format_caption`, `publish`, `get_analytics`)
  - `ModelRouter.route(task_type)` `core/model_router.py:99-125` + `generate_text()` `core/model_router.py:127-183` + fallback chains `config/models.yaml:146-154`
  - `BrandService.analyze_brand_voice()` `services/brand_service.py:76-150`
  - `DraftService.create→approve` `services/draft_service.py:24-142`
- **Implement:** No code unless mismatch found; add `SPEC_SHEET.md:41-105` architecture comment to `agents/orchestrator.py:1`.
- **Verification Gate S0:** `cli.py preview <url> --tone casual` → `DRAFT_ID` + `CAPTION` prints; `cli.py brand list` shows `DefaultBrand [ACTIVE]`; status all healthy.

---

## S1 — Intelligence Depth (Weekly Brief + Trend Detection)

**Spec:** `PRD.md:292-330`, `SPEC_SHEET.md:606-756`. **Current:** `services/trend_service.py:17-44` pytrends only, `services/competitor_service.py:15-55` no fetch, `agents/research_agent.py:24-70` naive concat.

### S1.1 TrendService v2 — Multi-Source Fetch + Scoring

**Design:** `services/trend_service.py:13-80` upgrades to 3 sources with brand-niche relevance scoring + `trend_insights` persistence `db/setup_db.py:130-141`.

- **Implement:**
  - [ ] Refactor `fetch_trending_topics(category, keywords)` `services/trend_service.py:17-44`:
    - Keep `pytrends.request.TrendReq` path with `kw_list` derived from `BrandService.get_active()` niche or `config/platforms.yaml` categories; `timeframe='now 7-d'`, `cat=0`; collect `rising` top 3/topic.
    - On exception → curated fallback already exists `services/trend_service.py:39-44` keep but log `mask_secrets`.
  - [ ] Add `fetch_x_trends()` — X API v2 free (`1500 tweets/mo` `PRD.md:401`). If `TWITTER_API_KEY` absent → skip gracefully. Parse `trends/place` or filtered `tweets/count` relevance.
  - [ ] Add `fetch_ig_hashtag_trends()` — stub via Composio public endpoints or `adapters/instagram.py:1` hashtag volume; rate-limit guarded.
  - [ ] Add `score_relevance(topic, brand_niche)` heuristic: `0.0-1.0` based on keyword overlap + `trend_velocity`. Filter `relevance_score >=0.6` before `save_trend()`.
  - [ ] Extend `save_trend()` `services/trend_service.py:48-59` to persist `trend_velocity`, `relevance_score`, `suggested_content='[]'`, `expires_at = NOW() + 7 days` `db/setup_db.py:138-140`.
  - [ ] Update `get_latest_trends()` `services/trend_service.py:61-80` to `WHERE expires_at > NOW() OR expires_at IS NULL`, order `relevance_score DESC`, limit 10.

- **Test (implement→test→debug loop):**
  - [ ] Unit `tests/test_trend_v2.py` (new): mock `pytrends.related_queries` returns 2x rising → 6 signals; mock no-creds X → skipped; expiry filter drops old rows.
  - [ ] Integration: seed 15 rows with mixed `expires_at`, assert `get_latest_trends()` returns 10 valid sorted.
  - [ ] Manual: `python cli.py trends` `cli.py:230-235` prints `topic (source) - Velocity: RISING` with at least 3 distinct `source` values when keys present.

- **Debug checklist:** `pytrends` 429 → backoff + fallback; `TrendReq` import missing → `import logging` already `services/trend_service.py:6` keep silent; secrets in log → `mask_secrets`.

- **Verification Gate S1.1:** `TrendService().fetch_trending_topics()` returns ≥3 signals with `relevance_score`; `trend_insights` rows have `expires_at` future; `cli.py trends` non-empty.

### S1.2 Competitor Fetch + Gap Storage

**Design:** `services/competitor_service.py:15-55` + `db/setup_db.py:118-128 competitor_posts` + `SPEC_SHEET.md:606-615`.

- **Implement:**
  - [ ] Add `sync_competitor_posts(competitor_id)` `services/competitor_service.py:39-55`:
    - Resolve `handle, platform` from `competitors` `db/setup_db.py:106-116`.
    - Call `adapters/instagram.py` via Composio `INSTAGRAM_GET_IG_USER_MEDIA` (public) or Meta Graph fallback; handle `COMPOSIO_API_KEY` missing → mark `last_scraped_at` but no rows.
    - For each media: `caption_summary` = summarize via `core/model_router.py:127 generate_text('fast_formatting', ...)` or raw first 200 chars if no LLM; `estimated_engagement = (likes+comments)/follower_count` heuristic else 0.0.
    - Upsert to `competitor_posts` `services/competitor_service.py:48-52` with `platform_post_id` unique, `posted_at`, `scraped_at`.
    - Update `competitors.avg_engagement_rate`, `last_scraped_at`.
  - [ ] Add `get_competitor_posts_last_7_days(brand_id)` helper for brief.
  - [ ] CLI `cli.py:216-228 cmd_competitors` add `--sync` flag to trigger sync; keep `--add` `cli.py:217-225 sanitizes handle` `core/security.py:sanitize_handle`.

- **Test:**
  - [ ] Unit: mock Composio 3 posts → 3 `competitor_posts` rows + `avg_engagement_rate` computed.
  - [ ] Integration: `add_competitor("@test")` → `sync` → `list_competitors()` shows `last_scraped_at` not null.
  - [ ] Manual: `python cli.py competitors --add @natgeo` then `--brief` shows handles.

- **Verification Gate S1.2:** `competitors` row + ≥1 `competitor_posts` row after sync; `ResearchAgent.analyze_competitors()` sees real data not `"No competitors tracked yet."` `agents/research_agent.py:55-56`.

### S1.3 Weekly Strategy Brief v2 — Analyst-Grade Synthesis

**Design:** `agents/research_agent.py:24-70` + `SPEC_SHEET.md:718-755`, `PRD.md:309-330`.

- **Implement:**
  - [ ] Rewrite `generate_weekly_brief(brand_id)` `agents/research_agent.py:24-48`:
    - Fetch `trends = TrendService.get_latest_trends(brand_id)` (relevance sorted) → `trends_text`.
    - Fetch `competitors + competitor_posts_last_7d` via S1.2 helper → `format_competitor_data`.
    - Fetch `own_performance = AnalystAgent.analyze_performance(days=7)` `agents/analyst_agent.py:1` or `db/repository.py:get_post_history` + `analytics_cache` `db/setup_db.py:211-219`.
    - Fetch `brand_profile = BrandService.get_active()` `services/brand_service.py:21-33` (tone, hooks).
    - Build prompt per `SPEC_SHEET.md:732-751` + `prompts/trend.py:build_trend_synthesis_prompt` + `prompts/competitor.py:build_competitor_analysis_prompt` with `system_prompt` brand voice injection `PRD.md:123-141`.
    - Route `core/model_router.py:127 generate_text(task_type='deep_analysis', max_tokens=800)` fallback chain `config/models.yaml:152 deep_analysis=[gemini_pro,mistral,openai]`.
    - Force strict JSON via `core/security.py:extract_json_from_llm`: `{performance_summary:2 sentences, competitor_spotlight, trending[3], content_ideas[5:{topic,platform,format,draft_hook,suggested_media}]}`. On parse fail → retry with `fast_formatting` Cerebras.
    - Persist each idea to `content_ideas` `db/setup_db.py:142-155` with `week_number=isocalendar().week`, `status='SUGGESTED'`, `source_trend_id`.
  - [ ] Update `analyze_competitors()` `agents/research_agent.py:50-70` to use real `competitor_posts` + `own_performance_text`.
  - [ ] CLI `cli.py:237-240 cmd_ideas` renders Markdown brief (header `📊 Weekly Content Intelligence — Week N`) + pretty-prints 5 ideas; `cli.py:230-235 trends` filtered by niche.

- **Test:**
  - [ ] Unit: mock router returns JSON brief → assert 5 `content_ideas` inserted, `relevance_score` filtered.
  - [ ] Integration: `TrendService` 3 topics + `CompetitorService` 2 handles + 4 posts → `generate_weekly_brief()` returns non-empty `performance_summary` + 5 ideas.
  - [ ] Failure: `AllProvidersExhausted` `core/exceptions.py:1` → user-friendly `"No reasoning providers. Set GEMINI_API_KEY or MISTRAL_API_KEY"` `core/security.py:mask_secrets`.

- **Verification Gate S1.3:** `python cli.py ideas` prints PRD-style brief with 5 ideas; `SELECT COUNT(*) FROM content_ideas WHERE week_number=?` =5; `deep_analysis` provider logged in `ai_calls` `db/setup_db.py:157-171`.

### S1.4 Scheduling — Monday 09:00 Push

- **Implement:**
  - [ ] Add `pipelines/scheduler.py:1` or `services/scheduler_service.py:54-95` APScheduler job `CronTrigger(day_of_week='mon', hour=9, timezone=POST_TIMEZONE)` `POST_TIMEZONE` `.env.example:55` default `Asia/Kolkata`. Calls `ResearchAgent.generate_weekly_brief()` + sends via Telegram `services/engagement_service.py:1` or `pipelines/dm-comments.py:1` if `TELEGRAM_BOT_TOKEN` set.
  - [ ] Add `python cli.py ideas --cron` flag for `scheduler.sh:1` cron alternative.
  - [ ] Cache last brief in `analytics_cache` or `trend_insights.suggested_content` to avoid regenerating within 24h.

- **Test:** Simulate Monday trigger → brief generated + cached; double-trigger within 1h returns cache.

- **Gate S1 DONE:** `cli.py trends` (niche-relevant, 3 sources), `cli.py competitors` (gap), `cli.py ideas` (5 persisted ideas, Monday job registered) all GREEN.

---

## S2 — UX Sophistication (Telegram Human-in-the-Loop)

**Spec:** `SPEC_SHEET.md:858-900`, `PRD.md:369-395`, `SKILLS.md:1-59`. **Current:** shell wrappers `post-preview.sh:1-3`, `post-approve.sh:1`, `cli.py:132-175 preview/approve/reject/update` plain text, no keyboards.

### S2.1 OpenClaw Skill Manifests

- **Design:** `info/openclawsetup.md:1-47` onboarding, `openclaw-config/openclaw.example.json:1-13` allowlist.
- **Implement:**
  - [ ] Create `.openclaw/skills/instagram-post/SKILL.md`, `instagram-carousel`, `instagram-drafts`, `instagram-generate`, `instagram-analytics`, `instagram-dm`, `instagram-scheduler` per `SKILLS.md:5-59`. Each `SKILL.md` declares `description`, `trigger`, `command` mapping to `~/post-to-instagram.sh` etc `post-to-instagram.sh:1`, `post-carousel.sh:1`, `generate-image.sh:1`.
  - [ ] Update `openclaw-config/openclaw.example.json` with 7 skills + `channels.telegram.allowFrom` + `agents/orchestrator.py:1` intent routing table.
  - [ ] Add `openclaw.jsonc` if missing: `model: anthropic/claude-haiku-4-5`, skills list, hooks `session-memory` `info/openclawsetup.md:18-31`.

- **Test:** `openclaw skills list` shows 7; `openclaw gateway run` `info/openclawsetup.md:33-36` no config error.

### S2.2 Telegram Bot Layer — Inline Keyboards + Callback Flow

**Design:** `SPEC_SHEET.md:858-876` layouts.

- **Implement:**
  - [ ] New `telegram/bot.py` (or `adapters/telegram.py`):
    ```python
    # handlers: MessageHandler(filters.PHOTO) -> DraftService.create()
    # CallbackQueryHandler(pattern="approve:\d+") -> DraftService.approve()
    ```
    - On `PHOTO/FILE_URL`: `validate_safe_url` `core/security.py:1`, `VisionAgent.describe_image()` `agents/vision_agent.py:1`, `CreatorAgent.generate_caption()` via `DraftService.create()` `services/draft_service.py:24-99` with `caption_variants[2]`.
    - Render preview card Markdown + image URL + `Draft #47` header `PRD.md:372-381`:
      ```
      🖼️ Draft Preview #47 — BrandX
      Caption: "... 🌿" (A/B: "... alt")
      Platform: Instagram + LinkedIn | Tone: Professional
      Row1: [✅ Approve & Post] [⏰ Schedule]
      Row2: [✏️ Edit Caption] [🔄 Change Tone]
      Row3: [🎨 Regenerate Image] [📱 Add Platform]
      Row4: [❌ Discard]
      ```
      Build via `telegram.InlineKeyboardMarkup` per `SPEC_SHEET.md:858-864`.
    - Brand switcher `SPEC_SHEET.md:868-871`: `/brand` → keyboard `[🏷️ BrandX (active)] [🏷️ ClientY]` → `BrandService.switch_brand()` `services/brand_service.py:41-44`.
    - Analytics quick actions `SPEC_SHEET.md:872-876`: `/analytics` → `[📊 Last 7 Days] [📊 Last 30 Days]` → `AnalystAgent.analyze_performance()` `agents/analyst_agent.py:1`.
    - All user text `sanitize_user_input(max_length=2200)` `core/security.py:1` + `<user_input>` sandbox per `PRD.md:431-438`.

  - [ ] Add `telegram/callbacks.py` routing `approve`, `reject`, `schedule`, `edit`, `regenerate`, `add_platform`, `change_tone` → `PublisherAgent.publish()` `agents/publisher_agent.py:1` via `adapters/instagram.py:1` `COMPOSIO` flow `flowchart.md:194-227`.
  - [ ] Allowlist middleware: `openclaw-config/openclaw.example.json:7 allowFrom` check, else silent drop `PRD.md:431`.

- **Test (loop):**
  - [ ] Unit `tests/test_telegram_ux.py` (new): mock `DraftService.create()` returns id 47 → assert keyboard has 4 rows, 7 buttons, callback_data `approve:47`.
  - [ ] Integration: `CallbackQuery(approve:47)` → `drafts` row deleted `services/draft_service.py:137 delete_draft` + `posts` row inserted `db/repository.py:174-204 log_post` + `ai_calls` logged.
  - [ ] Manual: Telegram send photo → preview <5s `PRD.md:443 <60s` → tap `✅ Approve & Post` → success with permalinks `adapters/base.py:PublishResult`.

- **Debug:** Callback timeout → answer `callback_query.answer()` within 3s; `validate_safe_url` SSRF block on private IP `tests/test_security.py:14`; double-tap approve → idempotent `get_draft()` null → `"Already posted"` not crash.

### S2.3 Draft Card Hardening

- **Implement:**
  - [ ] Extend `services/draft_service.py:24-99 create()` to return `brand_compliance_score` (`BrandService.check_compliance()` `services/brand_service.py:152-168`), `readability FK grade`, `alt_text` via Vision, `platforms` adaptation `adapters/base.py:MediaSpec` 1:1 vs 4:5.
  - [ ] `cli.py:132-152 cmd_preview` prints `DRAFT_ID`, `IMAGE_URL`, `CAPTION`, `VARIANTS`, `COMPLIANCE` for headless verification `flowchart.md:168-190`.

- **Verification Gate S2:** Telegram photo→keyboard preview→approve posts to IG (mock) within 60s; `/brand switch X` updates `is_active`; `post-preview.sh` + `post-approve.sh` still work headless `SKILLS.md:21-27`.

---

## S3 — Advanced Features (Repurposing + A/B)

**Spec:** `PRD.md:332-360`, `SPEC_SHEET.md:88-90`. **Current:** `services/repurpose_service.py:21-56` 4-field JSON, `services/draft_service.py:64-77` 2 variants no tracking.

### S3.1 Content Repurposing Engine v2

**Design:** `PRD.md:334-344` one → many.

- **Implement:**
  - [ ] Upgrade `services/repurpose_service.py:21-56 repurpose_article()`:
    - Inject brand context `BrandService.get_active()` `services/brand_service.py:21-33` + platform constraints `adapters/base.py:MediaSpec` caps `SPEC_SHEET.md:635-647` (IG 2200/30 tags, LinkedIn 3000/5, X 280/4 images, YouTube 5000).
    - System prompt enforces strict JSON + brand `prohibited_words`, `mandatory_elements` `services/brand_service.py:152-168`, `hashtag_count_range` `services/brand_service.py:116-119`.
    - Required output (validate via `core/security.py:extract_json_from_llm` `services/repurpose_service.py:47`):
      ```json
      {
        "twitter_thread": ["tweet1 ≤280", "...3-7"],
        "instagram_carousel_slides": ["Slide1: ...5-8"],
        "linkedin_post": "≤3000 chars professional",
        "quote_card_text": "1 sentence",
        "short_video_script": "30s Reels/Shorts"
      }
      ```
    - On `raw` too long for X → auto-thread split at sentence boundaries.
    - Persist: create `campaigns` row `db/setup_db.py:47-55 source_content=long_form_text` → then `posts` rows per platform `campaign_id`, `media_urls`, `status=PENDING` or via `DraftService.create()` for HITL.
  - [ ] CLI `cli.py:242-259 cmd_repurpose`: support `cli.py repurpose "text"` + `cli.py repurpose file.txt` with `validate_safe_file_path` `cli.py:249-255` already guarded; add `--brand <name>` + `--campaign` output.

- **Test:**
  - [ ] Unit: 800-word article `PRD.md:336` → 5 keys, X tweets ≤280, carousel 5 slides, LinkedIn ≤3000.
  - [ ] Integration: persisted `campaigns` + 3 `posts` rows (IG, LI, X); `router.generate_text(task_type='reasoning')` fallback chain `config/models.yaml:151 reasoning`.
  - [ ] Failure: empty input → graceful `long_form_text[:250]` fallback `services/repurpose_service.py:52` still branded.

- **Verification Gate S3.1:** `python cli.py repurpose file.txt` prints JSON with 5 keys + `campaign_id`; lengths enforce spec.

### S3.2 A/B Caption Testing + Performance Memory Loop

**Design:** `PRD.md:349-360` A/B, `SPEC_SHEET.md:672-700` Brand-Aware Prompt.

- **Implement:**
  - [ ] Extend `services/draft_service.py:24-99`:
    - `create(generate_variants=True)` always returns `caption_variants` JSON `db/setup_db.py:95` `["caption A","caption B","caption C"]` (2-3) at `temperature=0.85` for var2+; var1 at 0.7.
    - Telegram keyboard adds `[Use A] [Use B]` selector `SPEC_SHEET.md:858-864`.
    - `approve(draft_id, selected_variant_idx=0)` persists `selected_variant` `db/setup_db.py:96` + `caption_provider` `db/setup_db.py:68`, `brand_compliance_score` `db/setup_db.py:70` into `posts` log.
  - [ ] Add `services/performance_memory.py` (new) or extend `agents/analyst_agent.py:1`:
    - After `posted_at +48h`, `get_analytics()` `adapters/base.py:get_analytics` fetches `likes, comments, saves, engagement_rate` `db/setup_db.py:81-87`.
    - Job updates `ai_calls`, ranks hooks vs `brands.sample_hooks` `services/brand_service.py:136-138`, promotes top 20% hooks → `BrandService.update_profile()` `services/brand_service.py:51-74`.
    - Future `prompts/caption.py:build_caption_prompt` `services/draft_service.py:48-54` biases toward top hooks `SPEC_SHEET.md:676-701` `{top_hooks_from_history}`.

- **Test:**
  - [ ] Unit: `create()` returns 2-3 variants distinct (Levenshtein >0.3); `check_compliance()` flags prohibited words.
  - [ ] Integration: post variant A vs B, mock analytics 4.2% vs 1.1% → `sample_hooks` updates to A pattern after 48h cycle.
  - [ ] CLI: `python cli.py db ai_stats` `cli.py:289-293` shows per-variant `task_type=creative_writing`.

- **Verification Gate S3:** Variant selector works; 48h later `brands.sample_hooks` reflects winner; `BrandService.analyze_brand_voice()` `services/brand_service.py:76-150` still learns emoji/hashtag `avg_sentence_length` `PRD.md:133-145`.

- **Gate S3 DONE:** `repurpose` creates campaign + 3 platform posts; A/B winner propagates to brand memory.

---

## S4 — Deployment & Scale (SQLite → Redis/Cloudinary Ready)

**Spec:** `SPEC_SHEET.md:905-973`, `PRD.md:415-428`. **Current:** `requirements.txt:1-11` no queue, `db/repository.py:29-44` SQLite only, `services/scheduler_service.py:54-95` in-process, `services/media_host.py:1` imgbb only.

### S4.1 Database Abstraction — SQLite default, Postgres optional

- **Design:** `SPEC_SHEET.md:909-925` min vs team deployment.
- **Implement:**
  - [ ] Add `DATABASE_URL` env `.env.example:56` (e.g., `postgres://agent:pw@db/clawagent`). Keep `DB_PATH` default `db/uct_agent.sqlite` `db/repository.py:27`.
  - [ ] Refactor `db/repository.py:29-44 get_connection()` to factory: if `DATABASE_URL` startswith `postgres` → `psycopg2.connect` (add `psycopg2-binary` to `requirements.txt:1`), else SQLite WAL `PRAGMA journal_mode=WAL` `db/repository.py:39`.
  - [ ] Parameterize all queries `%s` vs `?` via helper; `get_storage_stats()` `db/repository.py:290-313` whitelist `ALLOWED_TABLES` `db/repository.py:20-24` unchanged.
  - [ ] Extend `db/migrate.py:1` + `db/setup_db.py:222-276 migrate_missing_columns` to run against both backends; add `alembic` stub if needed.
  - [ ] Keep `sqlite3.Row` compat: `dict(row)` `db/repository.py:73` works for both.

- **Test:**
  - [ ] Unit: mock `DATABASE_URL=postgres://...` → `get_connection()` returns psycopg2 cursor, `normalize_datetime_to_utc()` `db/repository.py:46-62` still `YYYY-MM-DD HH:MM:SS`.
  - [ ] Integration: `bash setup.sh` with SQLite → `pytest` green; switch `DATABASE_URL` to local Postgres → same 24 tests green.
  - [ ] Manual: `python cli.py db storage` works on both.

### S4.2 Queue — In-process default, Redis+CELERY optional

- **Implement:**
  - [ ] Add `requirements.txt` entries: `redis>=5.0`, `celery>=5.3`, `psycopg2-binary>=2.9`, `cloudinary>=1.36` behind optional import try/except.
  - [ ] Refactor `services/scheduler_service.py:54-95 process_due_posts()`:
    - If `REDIS_URL` unset → keep current loop `get_due_posts()` `db/repository.py:397-407` + `PublisherAgent.publish()` `services/scheduler_service.py:75-81`.
    - If `REDIS_URL` set → Celery app `celery_app.py` (new) tasks: `publish_scheduled_post(sched_id)` with `retry_count` `db/setup_db.py:197` + `last_error` `db/setup_db.py:198`; Beat schedule `every 60s` + weekly brief Monday 09:00.
    - Ensure UTC normalization `normalize_datetime_to_utc()` `db/repository.py:46-62` + `user_timezone` `db/setup_db.py:194` preserved.
  - [ ] Add `scheduler.sh:1` wrapper to choose `python cli.py scheduler --celery` vs `python pipelines/scheduler.py:1` fallback `flowchart.md:244-262`.

- **Test:**
  - [ ] Unit: enqueue 10 due posts → `get_due_posts()` correct where `status='PENDING' AND scheduled_time <= NOW()` `db/repository.py:401-404`; retry on `PublisherAgent` failure → `status='FAILED'` `db/repository.py:409-419 update_scheduled_status`.
  - [ ] Integration: kill Redis → fallback to in-process still posts; restart → no duplicate `mark_dm_seen()` `db/repository.py:347` idempotency.
  - [ ] Load: 100 `save_scheduled_post()` `db/repository.py:365-395` → beat drains queue without WAL lock `busy_timeout=15000` `db/repository.py:40`.

### S4.3 Media CDN — imgbb default, Cloudinary/S3 optional

- **Implement:**
  - [ ] Extend `services/media_host.py:1` (`MediaHostService.upload_from_url()`):
    - Env `MEDIA_PROVIDER=imgbb|cloudinary|s3` `.env.example:15` default `imgbb`; `IMGBB_API_KEY` `.env.example:15` free unlimited.
    - Add `cloudinary` uploader if `CLOUDINARY_URL` set; keep `Pillow` `requirements.txt:8` transform optional.
    - `PublisherAgent` `agents/publisher_agent.py:1` still calls `MediaHostService.upload_from_url()` before `adapters/instagram.py:1` `CREATE_MEDIA_CONTAINER`.
  - [ ] Handle `safe_stream_download` size limit 25MB `flowchart.md:302-303` + `validate_safe_url` SSRF `core/security.py:1`.

- **Test:** Mock `IMGBB_API_KEY` missing → fallback to `pollinations` direct URL; Cloudinary path uploads + returns CDN URL.

### S4.4 Docker & Deploy

- **Implement:**
  - [ ] Add `Dockerfile` (python:3.11-slim, `pip install -r requirements.txt:1`, `COPY . /app`, `CMD ["uvicorn","app:api","--host","0.0.0.0","--port","8080"]` or `python cli.py ai-status` healthcheck).
  - [ ] Add `docker-compose.yml` per `SPEC_SHEET.md:926-973`:
    ```yaml
    services:
      agent: {build: ., env_file: .env, volumes: [./config:/app/config, ./db:/app/db], depends_on: [redis, db], ports: ["8080:8080"]}
      worker: {build: ., command: celery -A celery_app worker, ...}
      scheduler: {command: celery -A celery_app beat, ...}
      redis: {image: redis:7-alpine}
      db: {image: postgres:15-alpine, env: {POSTGRES_DB: clawagent}}
    ```
  - [ ] Update `setup.sh:1` to detect `docker compose` vs local; `README.md:33-44 Quick Start` documents both.
  - [ ] Add FastAPI health `GET /api/v3/models/status` `SPEC_SHEET.md:770-782` + `POST /api/v3/models/reload` hot-reload `core/model_router.py:37-55 ConfigWatcher`.

- **Test:**
  - [ ] `docker compose config` valid; `docker compose up -d` → `curl localhost:8080/api/v3/models/status` returns `{cerebras:{status:healthy,circuit:CLOSED}}` per `SPEC_SHEET.md:778-782`.
  - [ ] `config/models.yaml:1` edit → watcher reloads within 5s `config/models.yaml:2-3 reload_interval_seconds` without restart `core/model_router.py:51-55`.

- **Verification Gate S4:** `DATABASE_URL` switch + `REDIS_URL` switch both GREEN; `docker compose up` healthy; `MEDIA_PROVIDER` switch posts successfully; `POST_TIMEZONE=Asia/Kolkata` `.env.example:55` respects IST scheduling.

---

## Cross-Cutting Tasks (run any time)

- **Security hardening** `core/security.py:1` — audit all new inputs via `validate_safe_url`, `validate_safe_file_path`, `sanitize_handle`; `mask_secrets` in `core/model_router.py:175-179` logs `ai_calls.error_message`.
- **Observability** — `db/setup_db.py:157-171 ai_calls` + `db/setup_db.py:172-180 circuit_breaker_events` + `core/model_router.py:258-263 _log_call` must log `provider, model, task_type, latency_ms, success` for every call `SPEC_SHEET.md:520-541`. `cli.py:289-293 db ai_stats` + `cli.py:261-268 ai-status` dashboards.
- **Prompt hygiene** — all LLM prompts wrap user text in `<user_input>` XML `PRD.md:431`, inject brand compliance before generation `services/brand_service.py:152-168`.
- **Cost guard** — enforce `cost_tier: free` default `config/models.yaml:22-54`; paid `enabled:false` never auto-fallback unless user toggles `config/models.yaml:102-135` + env key present `core/model_router.py:83-93 _has_credentials`.

---

## Workflow: How to Execute This Plan (Loop in Practice)

1. **Pick a slice** (e.g., S1.1 TrendService). Create branch `feat/S1-trend-v2`.
2. **Design** 15 min — write interface stub + DB delta + fallback table.
3. **Implement** vertical slice — smallest code that passes gate, behind `if os.getenv("TREND_V2")` if risky.
4. **Test** — run pyramid: unit (mock) → integration (SQLite) → manual CLI/Telegram.
5. **Debug** — if red, `python -c` reproduce, `git diff` isolate, fix, re-test. Repeat 3→4 until green.
6. **Review** — self-review `git log --oneline -5`, ensure no secret, no `.sqlite` commit, `tests/test_security.py` green.
7. **Merge** via `--no-ff`, delete branch, pull `main`, pick next slice.
8. **Parallel:** launch Task subagent for S2.1 manifests while you do S1.1 code — they touch disjoint files.

**Loop template command:**
```bash
python db/setup_db.py && python cli.py ai-status && python cli.py db storage
python tests/test_security.py; echo "---"; python tests/test_edge_cases.py
python cli.py trends && python cli.py competitors --brief && python cli.py ideas
```

**When stuck:** Check `flowchart.md:44-84` end-to-end flowchart, `db/repository.py:290-313` stats, `core/circuit_breaker.py:1` state `CLOSED→OPEN→HALF_OPEN` `SPEC_SHEET.md:339-353`.

---

## Verification Checklist — Final Gates (All must be GREEN)

- [ ] **G-S0** `python cli.py ai-status` healthy, `cli.py db storage` shows WAL, 24 tests green.
- [ ] **G-S1** `cli.py trends` (3 sources, relevance ≥0.6), `competitors --sync` → `competitor_posts`, `cli.py ideas` → 5 `content_ideas` persisted, brief Markdown PRD-style.
- [ ] **G-S2** Telegram photo → inline keyboard 4 rows → approve → `posts.status=POSTED` <60s; brand switch keyboard works.
- [ ] **G-S3** `cli.py repurpose "article"` → 5 keys length-checked + `campaigns` row; A/B variant B wins → `sample_hooks` updated after 48h mock.
- [ ] **G-S4** Switch `DATABASE_URL` postgres + `REDIS_URL` redis both green; `docker compose up` health endpoint green; `MEDIA_PROVIDER` toggle green.

---

## Appendix — Key References

- **PRD features:** `PRD.md:71-395` | **DB DDL 13 tables:** `db/setup_db.py:19-220` `SPEC_SHEET.md:359-582`
- **Model routing:** `core/model_router.py:92-287` + hot-reload `core/config_loader.py:1` + fallback `config/models.yaml:146-154`
- **Providers:** `providers/base.py:1`, `providers/openai_compatible.py:1`, `providers/google_genai.py:1`, `providers/pollinations.py:1`, `providers/replicate_provider.py:1`, `providers/banana_provider.py:1`
- **Adapters:** `adapters/instagram.py:1`, `adapters/linkedin.py:1`, `adapters/twitter.py:1`, `adapters/youtube.py:1`
- **Services:** `services/brand_service.py:76-168`, `services/draft_service.py:24-142`, `services/media_host.py:1`, `services/scheduler_service.py:54-95`, `services/repurpose_service.py:21-56`
- **CLI:** `cli.py:45-393` | **Pipelines (BackwardCompat):** `pipelines/ai_router.py:1`, `pipelines/scheduler.py:1` | **Skills:** `SKILLS.md:1-59`
- **Security tests:** `tests/test_security.py:14` SSRF, traversal, redaction | **Edge tests:** `tests/test_edge_cases.py:10` circuit breaker, concurrency

---

*Planmuse complete — execute slice-by-slice via Design→Implement→Test→Debug→Review→Record loop. Parallelize disjoint files. No slice is DONE until its Gate is GREEN and `main` tests remain GREEN.*
