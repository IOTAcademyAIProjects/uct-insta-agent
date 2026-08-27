# BUGFIX PLAN — ClawAgent v3.1 Deep Audit

**Date:** 2026-08-28  
**Auditor:** Muse Spark (full codebase read: `core/*`, `db/*`, `services/*`, `agents/*`, `adapters/*`, `providers/*`, `pipelines/*`, `telegram/*`, `api.py`, `cli.py`, `celery_app.py`)  
**Total findings:** 43 — 13 Critical, 15 High, 15 Medium/Low  
**Implementation strategy:** Fix CRITICAL first (data loss/crash), then HIGH (wrong behavior), then MEDIUM (perf/edge). Each fix gated by `python tests/test_security.py && tests/test_edge_cases.py` + manual `cli.py` gates `Planmuse.md:16`.

---

## CRITICAL — Fix immediately (ship blocking)

| ID | File:Line | Bug | Impact | Fix |
|---|---|---|---|---|
| **C-01** | `db/repository.py:34` `_PostgresConnWrapper` single cursor + `?→%s` naive | Thread-unsafe cursor interleaves; `?` in string literal corrupted; `PRAGMA` dummy shape mismatch | Team deploy silent wrong counts / crash | Per-execute new cursor `RealDictCursor`, parse placeholders safely, return shaped dummy; or use `psycopg2.pool` |
| **C-02** | `db/repository.py:98` + `db/setup_db.py:279` FK never enabled | `REFERENCES` ignored → orphans | Data integrity loss | `PRAGMA foreign_keys=ON` on every `get_connection` + `setup_database` |
| **C-03** | `db/repository.py:250,409,283` `INSERT OR REPLACE/IGNORE` | Postgres `syntax error at or near "OR"` — all writes crash on `DATABASE_URL=postgres` | Team deploy 100% writes fail | Branch on `get_database_url()` → `ON CONFLICT` syntax; fallback sqlite path |
| **C-04** | `core/security.py:113` `safe_stream_download` `allow_redirects=True` no re-validate | `https://public/redirect?to=169.254.169.254` bypasses `validate_safe_url` | Full SSRF → cloud metadata | `allow_redirects=False` + loop validate each `Location`, or validate `response.history` |
| **C-05** | `core/security.py:87` `allowed_base_dirs=None` permits any path | Only basename blocklist; `../../etc/passwd` passes | Arbitrary file read via `media_host`/`cli repurpose` | Default to `PROJECT_ROOT` when None, enforce `commonpath` must equal `real_base`, handle `ValueError` |
| **C-06** | `services/draft_service.py:167` draft deleted even on `publish` failure | `delete_draft` outside success check | Failed post unrecoverable | Delete only if `all(r.success)` else keep `PENDING` + error |
| **C-07** | `db/repository.py:130` `get_active_brand` race `INSERT` duplicate `name` UNIQUE | Concurrent `SELECT 0` → both `INSERT` same `DefaultBrand` → `IntegrityError` unhandled | 500 on parallel startup | `INSERT OR IGNORE` + re-SELECT, catch `IntegrityError`, `BEGIN IMMEDIATE` |
| **C-08** | `core/circuit_breaker.py:54` `is_open` mutates `OPEN→HALF_OPEN` + probe slot | `ModelRouter:114,150` checks `is_open` steals probe | Healthy provider starved | Make `is_open` side-effect-free; add `try_probe()` explicit |
| **C-09** | `telegram/bot.py:20` allowlist dev `return True` | No config → all users allowed | Unauthorized publish/brand switch/improve approve | Fail-closed `return False`; require `ALLOW_OPEN=true` for dev |
| **C-10** | `pipelines/*` `client.tools.execute(slug=...)` vs `adapters/instagram.py:145` `client.actions.execute(action=...)` | AttributeError legacy vs new `composio-core` | All legacy pipelines crash | Unify to `actions`; wrapper version-agnostic |
| **C-11** | `services/media_host.py:102` `open().read()` unbounded 25MB → 33MB b64 | No `getsize` check before read | OOM DoS | `os.path.getsize` reject >25MB; stream `iter(f.read(64k))` |
| **C-12** | `adapters/instagram.py:133` `sleep(3)` fixed vs polling `status_code` | Video/carousel >3s → `ERROR` not retried | Publish fails intermittently | Poll `GET /{creation_id}?fields=status_code` exponential backoff 30s |
| **C-13** | `telegram/bot.py:159` `file.file_path` bare `photos/file_57.jpg` | No scheme/host → `validate_safe_url` fails | Telegram photo upload always fails | Build `https://api.telegram.org/file/bot{token}/{file_path}` or `download_to_drive` |

---

## HIGH — Wrong behavior, silent logic bugs

| ID | File:Line | Bug | Fix |
|---|---|---|---|
| **H-01** | `db/repository.py:108` `normalize_datetime_to_utc` drops `+05:30` or naive `POST_TIMEZONE` | Pass `user_tz` `ZoneInfo`, attach before conversion; don't strip `T` blindly |
| **H-02** | `db/repository.py:459` `scheduled_time <= now_utc` lexical with mixed `YYYY-MM-DD HH:MM` vs `...:SS` | Store normalized `%Y-%m-%d %H:%M:%S` always; coerce on read via `fromisoformat` |
| **H-03** | `services/scheduler_service.py:57` + `self_improvement_service.py:225` ISO `week` without `year` | Store `year*100+week` or `YYYY-WW`; migrate `improvement_log.week_number` → `year_week` |
| **H-04** | `db/repository.py:181` `switch_active_brand` two `UPDATE` non-atomic | `BEGIN IMMEDIATE; UPDATE 0; UPDATE 1; COMMIT` rollback on fail |
| **H-05** | `services/scheduler_service.py:117` `process_due_posts` only checks `INSTAGRAM` | Check `any(r.success)` or per-platform `scheduled_post_platform_status` table |
| **H-06** | `services/media_host.py:111` `detect_media_type` `HEAD` follows redirect to private IP | `allow_redirects=False` + re-validate `Location`; `timeout=5` |
| **H-07** | `db/repository.py:377` `get_post_history` `timestamp` vs `created_at/posted_at` column mismatch + `SELECT *` vs unpack 6 cols | Align to `COALESCE(timestamp, created_at, posted_at)` |
| **H-08** | `api.py:44` `/models/reload` no schema validation, partial `clear()` bricks | Validate JSONSchema before `clear()`, keep old config on fail |
| **H-09** | `core/model_router.py:83` `_has_credentials` blocks `ollama` (type `openai_compatible` localhost) | Check `api_key_env=="OLLAMA_PLACEHOLDER"` or `base_url` contains `localhost:11434` → True |
| **H-10** | `services/competitor_service.py:106` mock dedup only when `COMPOSIO_API_KEY` absent | Always dedup by `platform_post_id ON CONFLICT`, regardless of key |
| **H-11** | `services/brand_service.py:51` `update_profile` SQLi via `f"{k} = ?"` | Whitelist `k` against `ALLOWED_FIELDS` inside method |
| **H-12** | `agents/analyst_agent.py:24` `datetime.now()` local vs UTC | `datetime.now(timezone.utc)` |
| **H-13** | `pipelines/db_manager.py:14` hardcoded `DB_PATH` ignores `get_db_path()` + no `PRAGMA busy_timeout` | Use `get_connection()` |
| **H-14** | `providers/google_genai.py:92` `describe_image` no `finish_reason` safety check | Copy same SAFETY block check as `generate_text` |
| **H-15** | `services/draft_service.py:127` `brand.get("id",1)` without `brand is None` guard | `(brand or {}).get("id",1)` |

---

## MEDIUM — Perf / Edge / Degraded

M-01 `db/repository.py:352` N+1 `COUNT(*)` 5 queries — `UNION ALL` + add indexes `posts(brand_id,timestamp)`, `scheduled_posts(status,scheduled_time)`  
M-02 `db/repository.py:399` `get_seen_dms` unbounded `SELECT` — add `LIMIT 1000` or `WHERE seen_at > -30d`  
M-03 `core/security.py:75` `socket.getaddrinfo` blocks Telegram async — use `asyncio` or `concurrent.futures` timeout  
M-04 `core/security.py:167` `sanitize_user_input` only exact `<user_input>` — use case-insensitive `re.sub(r"</?user_input\s*>", ..., flags=re.I)`  
M-05 `services/trend_service.py:210` niche from `tone_of_voice` — use explicit `brand_niche` column  
M-06 `services/repurpose_service.py:76` campaign + posts not transactional — single transaction  
M-07 `services/performance_memory.py:43` winner hooks overwritten by `analyze_brand_voice` — remove second call or preserve  
M-08 `services/repurpose_service.py:27` thread `enforced[:7]` truncation after loop — ensure `enforced = enforced[:7]`  
M-09 `celery_app.py:31` fixed 7d interval not `crontab` — use `crontab(hour=9, minute=0, day_of_week=1)`  
M-10 `providers/pollinations.py:54` no `stream` + `Content-Length` check — `stream=True` + magic-byte  
M-11 `services/engagement_service.py:36` `get_dms` returns all not `new_conversations` — fix return  
M-12 `services/scheduler_service.py:98` `trigger_self_improve` missing year-week guard — query `year_week`  
M-13 `pipelines/preview.py:147` `POSTED` vs `DELETE` inconsistency — standardize DELETE  
M-14 `adapters/linkedin.py:57` media ignored `shareMediaCategory=NONE` — implement `registerUpload`  
M-15 `providers/replicate_provider.py:37` `width/height` ignored `1:1` — map to `aspect_ratio`

---

## LOW — Minor (deferred unless touched)

L-01 `uct` vs `utc` typo, L-02 `observer.daemon`, L-03 brand keyboard case, L-04 `cmd_post` prints then publishes, L-05 `api_health` HALF_OPEN count, L-06 Alpine psycopg2, L-07 `avg_sentence_length` None cast, L-08 sentence split, L-09 `seed` entropy, L-10 `migrate.py` timeout, L-11 Telegram token regex, L-12 `clear_drafts` rowcount.

---

## Execution Order

1. **CRITICAL DB+Security** (C-02 FK, C-04 SSRF redirect, C-05 traversal, C-06 draft loss, C-08 CB, C-09 allowlist) — must land before any data loss.
2. **CRITICAL Integration** (C-01 PG wrapper, C-03 ON CONFLICT, C-10 composio, C-12 IG poll, C-13 Telegram file)
3. **HIGH Logic** (H-03 week-year, H-04 transaction, H-11 SQLi whitelist, H-08 reload validation)
4. **MEDIUM Perf** (indexes, limits) — after functional.
5. **LOW** — opportunistic.

Each fix verified by: `python tests/test_security.py` 14 OK + `tests/test_edge_cases.py` 10 OK + `python cli.py db storage / preview / improve propose` + `TestClient(api.app).get('/health')`.
