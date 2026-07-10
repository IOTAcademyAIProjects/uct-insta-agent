# uct-insta-agent

AI-powered Instagram management via Telegram — built with OpenClaw, Anthropic Claude, Composio MCP, and Google Gemini.

**Built by:** Uniconverge Technologies Pvt. Ltd.
**Website:** www.uniconvergetech.in

---

## Milestone Progress

| # | Milestone | Status |
|---|---|---|
| M1 | Environment setup & base agent | Done |
| M2 | Single image posting | Done |
| M3 | AI captions & scheduling | Done |
| M4 | Carousel / multi-image posts | Done |
| M5 | Single video posting (URL-based) | Done |
| M6 | Analytics dashboard (date range + content-type insights) | Done |
| M7 | Composio MCP - DMs & comments | Pending |
| M8 | Gemini AI image generation | Pending |
| M9 | Gemini AI short video generation | Pending |
| M10 | Stories & advanced scheduling | Pending |
| M11 | Open source packaging & docs | Pending |

---

## Quick Start

    git clone https://github.com/IOTAcademyAIProjects/uct-insta-agent
    cd uct-insta-agent
    cp .env.example .env
    # fill in your API keys in .env
    bash setup.sh
    openclaw gateway run

---

## Requirements

- Node.js v18+
- Python 3.11+
- Lightning.ai 24GB GPU Studio (M8/M9 only)
- Accounts: Telegram, Anthropic, Composio, imgbb, Google AI Studio

---

## Tech Stack

| Technology | Purpose |
|---|---|
| OpenClaw | Agent runtime & Telegram bot framework |
| Multi-AI Router | Captions, summaries — rotates across NVIDIA, Cerebras, Mistral (free) |
| Composio MCP | Instagram publishing, DMs, comments, analytics |
| Google Gemini | AI image & short video generation (M8/M9) |
| imgbb | Free image hosting - public URLs for Instagram API |
| Lightning.ai | 24GB GPU cloud studio for M8/M9 |
| Node.js v18+ | OpenClaw runtime environment |
| Python 3.11 | Image/video/analytics pipelines |
| SQLite | Local draft post storage |

---

## Environment Variables

Copy .env.example to .env and fill in your keys.

| Variable | Purpose | Source |
|---|---|---|
| ANTHROPIC_API_KEY | Claude API | console.anthropic.com |
| TELEGRAM_BOT_TOKEN | Telegram bot | @BotFather |
| COMPOSIO_API_KEY | Composio MCP | dashboard.composio.dev |
| COMPOSIO_ACCOUNT_ID | Instagram auth config ID | Composio Auth Configs |
| INSTAGRAM_USER_ID | Numeric Instagram Business ID | INSTAGRAM_GET_USER_INFO tool |
| IMGBB_API_KEY | Image hosting API key | api.imgbb.com |
| OPENCLAW_MODEL | Claude model | anthropic/claude-haiku-4-5 |
| GPU_ENABLED | Enable GPU pipelines | true or false |
| POST_TIMEZONE | Default timezone for scheduling | e.g. Asia/Kolkata |
| GEMINI_API_KEY | Gemini image/video gen (M8/M9) | aistudio.google.com |

---

## Repository Structure

    uct-insta-agent/
    |-- skills/
    |   |-- instagram-post-image.js
    |   |-- caption-generator.js
    |-- pipelines/
    |   |-- post-with-caption.py       # IMAGE + VIDEO posting pipeline
    |   |-- post-carousel.py           # Multi-image carousel pipeline
    |   |-- get-analytics.py           # Analytics + content-type insights
    |-- lightning/
    |   |-- app.py
    |-- db/
    |   |-- drafts.sqlite
    |-- info/
    |   |-- openclawsetup.md
    |   |-- telegramsetup.md
    |-- openclaw-config/
    |   |-- openclaw.example.json
    |-- .github/workflows/
    |   |-- ci.yml
    |-- setup.sh                       # One-command session restore
    |-- post-to-instagram.sh           # Shell bridge - image/video posting
    |-- post-carousel.sh               # Shell bridge - carousel posting
    |-- post-analytics.sh              # Shell bridge - analytics
    |-- test-m2.py
    |-- test-imgbb.py
    |-- .env.example
    |-- package.json
    |-- README.md

---

## Bot Details

| Field | Value |
|---|---|
| Bot Name | UCT ClawGram |
| Bot Username | @uct_clawgram_bot |
| Instagram Account | @iot_academy_projects |
| Platform | Telegram Bot API via OpenClaw |

---

## How It Works

    User sends message on Telegram
               |
               v
    OpenClaw receives and passes to Claude
               |
               v
    Claude reads skill files and decides action
               |
               v
    Shell script triggers Python pipeline
               |
               v
    Pipeline calls Composio (post / fetch insights)
               |
               v
    Claude generates caption or summary
               |
               v
    Bot replies on Telegram

---

## Milestone Highlights

### M4 - Carousel Posts
Collects 2-10 images, uploads each to imgbb, creates individual carousel
child containers via Composio, then publishes them as one swipeable post
with a single unified Claude-generated caption.

### M5 - Video Posting
post-with-caption.py auto-detects IMAGE vs VIDEO from HTTP content-type
headers and posts accordingly (photo vs reel). URL-based video posting is
confirmed working end-to-end from Telegram. Direct phone file upload is
deferred due to a known OpenClaw 2026.5.7 media pipeline limitation
(tracked upstream as issue #18577) - users currently provide a public
video URL rather than attaching a file directly.

### M6 - Analytics Dashboard
get-analytics.py supports three modes: default last 7 days, a custom
number of days, or a fully custom date range (start and end date). It
ranks performance by content type (image vs video vs carousel) using
average reach and engagement, then asks Claude to produce a plain-English
summary with a concrete content recommendation - for example, identifying
that video content is outperforming images and should be prioritized.

This module's research and methodology - including the content-type
performance ranking approach and date-range handling design - was
researched and contributed by Raja, who worked closely with Abhishek to
get the analytics pipeline production-ready.

---

## Contributors

| Name | Role | Contribution |
|---|---|---|
| Abhishek Kumar Shukla | Senior AI Developer | Project lead, Lightning.ai environment, M1 OpenClaw setup, M2 Composio integration, M3 Claude caption pipeline, M4 carousel posting, M5 video posting, M6 analytics implementation, Telegram bot wiring, overall architecture |
| Drupad Das | AI Developer | Co-developer, Windows local environment, milestone collaboration, code review |
| Manish | AI Developer | Contributed video support architecture - auto content-type detection (IMAGE vs VIDEO), video URL handling, content_type field (reel/photo) - integrated into post-with-caption.py for M5 |
| Raja | AI Developer | Researched and assisted with the M6 Analytics module - content-type performance ranking methodology and date-range handling design, working closely with Abhishek on implementation |

---

## Session Restore (Lightning.ai)

Every new Lightning.ai session requires:

    cd ~/uct-insta-agent
    git pull origin main
    npm install -g openclaw
    bash setup.sh
    # fill in .env with your API keys
    openclaw gateway run

---

## Security Notes

- Never commit .env - it is in .gitignore
- Rotate all tokens before M11 public release
- Bot DM policy is set to allowlist - only approved Telegram IDs can interact
- Run openclaw security audit regularly

---

## License

MIT - free to clone, modify, and self-host.

(c) 2025 Uniconverge Technologies Pvt. Ltd.
