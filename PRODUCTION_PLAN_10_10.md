# Production 10/10 Plan — ClawAgent v3.1 → v4.0 Enterprise

**Goal:** From current **5.0/10** `ENTERPRISE_REVIEW_v3.1.md:1` to **10/10** OpenClaw enterprise (architecture, error handling, typing, tests, async, rate limiting).  
**Principles:** Ship safety first, $0 default, no `except: pass`, `mypy --strict`, 80% cov, async non-blocking, token bucket.

---

## Phase 1 — Core Architecture, Critical Bug Fixes, Hardening (NOW) ⭐

**Exit criteria:** All CRITICAL `BUGFIX_PLAN.md:1` C-01→C-13 fixed + `SECURITY_AUDIT.md:1` S-C01→S-C05 fixed, `tests/test_security.py` 14 OK + `tests/test_edge_cases.py` 10 OK + new `tests/test_phase1.py` 12 OK, `cli.py` gates GREEN, `TestClient(api.app)` health GREEN, no `FK` orphan, SSRF redirect blocked, allowlist denied, draft kept on failure, CB `is_open` no side-effect.

**Tasks (priority order, each `implement→test→debug`):**
1. **DB PG wrapper** `db/repository.py:34` per-execute new `RealDictCursor`, safe `?→%s` in-string aware, `PRAGMA foreign_keys=ON` both `get_connection` + `setup_database` — **done** verify `PRAGMA foreign_keys` 1.
2. **PG ON CONFLICT** `db/repository.py:250,409,283` — branch `get_database_url()` → `ON CONFLICT (post_id) DO UPDATE` etc. for `log_post`, `mark_dm_seen`, `add_competitor` — *Phase 1 remaining* (do now).
3. **Race `get_active_brand`** `db/repository.py:130` `INSERT OR IGNORE` + `IntegrityError` + `BEGIN IMMEDIATE` — **done**; add same for `create_brand` unique.
4. **Switch atomic** `db/repository.py:181` `BEGIN IMMEDIATE` — **done**.
5. **SSRF redirect** `core/security.py:113` `allow_redirects=False` loop re-`validate_safe_url` max 3 — **done**.
6. **Traversal default** `core/security.py:87` `PROJECT_ROOT_DEFAULT` fail-closed + `ValueError` — **done**.
7. **Prompt injection** `core/security.py:167` case-insensitive `re.sub` — **done**.
8. **Draft loss** `services/draft_service.py:167` delete only if `any(r.success)` — **done**.
9. **CB `is_open`** `core/circuit_breaker.py:54` side-effect-free + `try_probe()` — **done**.
10. **Allowlist** `telegram/bot.py:20` fail-closed `ALLOW_OPEN=true` only — **done**.
11. **Media OOM** `services/media_host.py:102` `getsize` >25MB reject — **done**; `detect_media_type` `HEAD` re-validate redirect — **done**.
12. **Telegram file_path** `telegram/bot.py:159` `https://api.telegram.org/file/bot{token}/...` — **done**.
13. **Composio wrapper** `adapters/instagram.py:26` `tools`↔`actions` proxy + `_poll_container_ready` exponential backoff 30s — **done**.
14. **Week-year** `services/self_improvement_service.py:222`, `services/scheduler_service.py:57`, `agents/research_agent.py:44` `year*100+week` — **done** (partial, need `content_ideas` migration check).
15. **Secrets** `core/security.py:143` expanded bot pattern `bot\d{7,12}:[...]{25,}` — **done**.
16. **Ollama creds** `core/model_router.py:83` localhost check — **done**.
17. **Reload validation** `api.py:44` schema check before `clear()` — **done**.
18. **Scheduler multi-platform** `services/scheduler_service.py:118` `any(r.success)` — **done**.
19. **Remaining Phase 1:** PG `log_post` etc. `ON CONFLICT`, `db/migrate.py` use `get_connection`, `providers/google_genai.py:92` `finish_reason` in `describe_image`, `pipelines/db_manager.py:14` use `get_db_path`, `services/competitor_service.py:106` dedup always.

**Verification:** `python tests/test_security.py && tests/test_edge_cases.py && tests/test_phase1.py` 36 OK, `python cli.py db storage && cli.py preview && cli.py improve propose`, `curl /health`, `curl /api/v3/self-improve/pending`.

**Effort:** 3 dev-days, no new deps.

---

## Phase 2 — Typing & Error Handling (Week 2)

**Goal:** `mypy --strict` 0 errors, no `except: pass`.

**Tasks:**
- Add `py.typed`, `TypedDict` `Brand`, `Post`, `Draft`, `Proposal` `db/repository.py:130`, `pydantic` models `api.py:17`.
- Replace `Dict[str, Any]` with precise types, `Literal["INSTAGRAM","LINKEDIN"]` for `PlatformAdapter`.
- `ruff` + `mypy` in `requirements-dev.txt`, `pre-commit` hook, CI `mypy` gate.
- Replace 14 `except Exception: pass` with `logger.exception` + `mask_secrets` + `Result` propagation.
- `providers/google_genai.py:92` copy `finish_reason` check to `describe_image`.

**Gate:** `mypy .` 0, `ruff check` 0, `AllProvidersExhausted` not swallowed.

---

## Phase 3 — Test Coverage 80% (Week 3)

**Goal:** `pytest --cov` ≥80% line, contract + integration.

**Tasks:**
- Add `pytest-cov`, `hypothesis`, `factory_boy` to `requirements.txt`.
- New suites: `test_trend_v2.py` (mock `pytrends`), `test_competitor_sync.py`, `test_research_brief.py` JSON persist, `test_draft_variants.py`, `test_self_improve.py` (propose/approve/measure + year_week), `test_telegram.py` keyboards/callbacks, `test_api.py` `TestClient`, `test_media_host.py` SSRF redirect, `test_repository_pg.py` (mock `psycopg2`).
- Contract tests `PlatformAdapter` `get_media_spec`/`publish`, `ProviderClient`.
- CI `coverage fail_under=80`.

**Gate:** `pytest --cov=services --cov=core --cov=adapters --cov-report=term-missing` 80.

---

## Phase 4 — Async & Concurrency (Week 4)

**Goal:** No blocking of Telegram async loop, `async` DB, correct beats.

**Tasks:**
- `core/security.py:75` `socket.getaddrinfo` → `asyncio.to_thread` with timeout 2s.
- `db/repository.py` → `aiosqlite` pool + `asyncpg` for PG; `get_connection` async variant; `get_due_posts` use `datetime.now(timezone.utc)` vs `ZoneInfo` `H-01` fix with `user_tz`.
- `celery_app.py:31` fixed 7d interval → `crontab(hour=9, minute=0, day_of_week=1)` for brief/improve.
- `switch_active_brand` `SELECT ... FOR UPDATE`, `get_due_posts` lexical fix `H-02` store normalized `%Y-%m-%d %H:%M:%S` + `CHECK`.
- `pipelines/` legacy removed, single `services/` path.

**Gate:** `telegram` photo→draft <2s p95, concurrent `process_due_posts` no WAL lock.

---

## Phase 5 — Rate Limiting & Observability + Final Hardening (Week 5)

**Goal:** Token bucket per `brand_id`+`provider`, `RateLimitExceeded` enforced, Prometheus.

**Tasks:**
- `slowapi` or `redis` token bucket `services/rate_limiter.py` per `brand_id` `provider` `limits` `config/models.yaml:15`; `ModelRouter.generate_text` checks `is_rate_limited` before `route`, raises `RateLimitExceeded` `core/exceptions.py:32` with `Retry-After`.
- `api.py:62` add `verify_bearer` + `X-Request-ID` + `slowapi` on `/intelligence/*`, `/self-improve/propose`.
- `structlog` JSON logs + `prometheus_client` `provider_latency_seconds`, `circuit_breaker_events` counter, Grafana.
- Supply chain `pip-compile --generate-hashes`, `docker-compose` read-only rootfs.
- Final audit `SECURITY_AUDIT.md` S-H01→S-M06 closed, `BUGFIX_PLAN.md` M-01→M-15 closed.

**Gate:** `locust` 100 RPS `improve propose` → 429, `prometheus` metrics, no `S-C` open.

---

## Execution Order (priority)

1. **Phase 1 now** (ship blocking) → verify 36 tests GREEN before merge.
2. Phases 2-5 parallelizable per file lock: typing vs tests vs async vs rate limit (different files).
3. Each phase `implement→test→debug` loop `Planmuse.md:16`, `git commit` per phase, `BUMP` `PRD.md:4` v3.1→v3.2→v4.0.

**10/10 Definition:** `mypy --strict` 0, `pytest --cov` 80, `ruff` 0, `async` non-blocking, `RateLimitExceeded` enforced, 0 `except: pass`, `FK` on, SSRF redirect blocked, allowlist fail-closed, draft kept on fail, CB correct, PG `ON CONFLICT`, IG polling, year_week, secrets expanded, `api` validated, `health` + `metrics` + `improvement_log` audit GREEN.
