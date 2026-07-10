# uct-insta-agent

AI-powered Instagram management via Telegram — built with OpenClaw,
Multi-AI Router (NVIDIA + Cerebras + Mistral), Composio MCP, and Pollinations AI.

**Built by:** Uniconverge Technologies Pvt. Ltd.
**Website:** www.uniconvergetech.in
**Bot:** @uct_clawgram_bot (UCT ClawGram)
**Instagram:** @iot_academy_projects

---

## Milestone Progress

| # | Milestone | Status | Owner |
|---|---|---|---|
| M1 | Environment setup & base agent | Done | Abhishek |
| M2 | Single image posting | Done | Abhishek |
| M3 | AI captions & scheduling | Done | Abhishek |
| M4 | Carousel / multi-image posts | Done | Abhishek |
| M5 | Single video posting (URL-based) | Done | Abhishek |
| M6 | Analytics dashboard (date range + content-type insights) | Done | Abhishek + Raja |
| M7 | DMs & comments + Telegram notifications | Done | Abhishek |
| M8 | AI image generation (Pollinations SDXL) | Done | Abhishek |
| M9 | AI video generation | Future scope | TBD |
| M10 | Stories & advanced scheduling (SQLite queue) | Done | Abhishek |
| M11 | Open source packaging & docs | Pending | TBD |

---

## Quick Start

    git clone https://github.com/IOTAcademyAIProjects/uct-insta-agent
    cd uct-insta-agent
    cp .env.example .env
    # fill in your API keys in .env
    bash setup.sh
    python3 db/setup_db.py
    openclaw gateway run

---

## Requirements

- Node.js v18+
- Python 3.11+
- Accounts: Telegram, Composio, imgbb, NVIDIA NIM, Cerebras, Mistral, Pollinations (free)
- No paid AI API required — all providers are free tier

---

## Tech Stack

| Technology | Purpose |
|---|---|
| OpenClaw | Agent runtime & Telegram bot framework |
| Multi-AI Router | Caption & summary generation — NVIDIA NIM, Cerebras, Mistral (all free) |
| NVIDIA NIM (z-ai/glm-5.2) | OpenClaw agent brain — free, no Anthropic key needed |
| Composio MCP | Instagram publishing, DMs, comments, analytics |
| Pollinations AI (SDXL) | AI image generation — free, no API key needed |
| imgbb | Free image hosting — public URLs for Instagram API |
| SQLite | Local database — posts, drafts, analytics, scheduling |
| Node.js v18+ | OpenClaw runtime environment |
| Python 3.11 | All pipelines and AI routing |

---

## Multi-AI Router

The project uses a Round Robin + Fallback AI router across 3 free providers.
No paid API keys required. Inspired by the OpenRouter multi-provider routing
architecture as explained by Raja.

| # | Provider | Model | Free Limit |
|---|---|---|---|
| 1 | NVIDIA NIM | z-ai/glm-5.2 | 40 RPM, 1000 credits |
| 2 | Cerebras | gpt-oss-120b | 1M tokens/day |
| 3 | Mistral | mistral-large-latest | ~1B tokens/month |

Round Robin ensures load is distributed evenly. Fallback automatically
switches to the next provider if one fails or hits rate limits.

---

## Environment Variables

Copy .env.example to .env and fill in your keys.

| Variable | Purpose | Source |
|---|---|---|
| TELEGRAM_BOT_TOKEN | Telegram bot | @BotFather |
| COMPOSIO_API_KEY | Composio MCP | dashboard.composio.dev |
| COMPOSIO_ACCOUNT_ID | Instagram auth config ID | Composio Auth Configs |
| INSTAGRAM_USER_ID | Numeric Instagram Business ID | INSTAGRAM_GET_USER_INFO |
| IMGBB_API_KEY | Image hosting API key | api.imgbb.com |
| NVIDIA_API_KEY | NVIDIA NIM (brain + captions) | build.nvidia.com |
| CEREBRAS_API_KEY | Caption generation | inference.cerebras.ai |
| MISTRAL_API_KEY | Caption generation | console.mistral.ai |
| GPU_ENABLED | Enable GPU pipelines | true / false |
| POST_TIMEZONE | Default timezone | e.g. Asia/Kolkata |
| DB_PATH | SQLite database path | db/uct_agent.sqlite |

---

## Repository Structure

    uct-insta-agent/
    |-- pipelines/
    |   |-- ai_router.py           # Multi-AI Router (NVIDIA + Cerebras + Mistral)
    |   |-- post-with-caption.py   # Image/video posting with AI caption
    |   |-- post-carousel.py       # Carousel posting (2-10 images)
    |   |-- get-analytics.py       # Analytics with custom date ranges
    |   |-- dm-comments.py         # DMs, comments, Telegram notifications
    |   |-- preview.py             # Draft preview flow
    |   |-- generate-image.py      # AI image generation (Pollinations)
    |   |-- scheduler.py           # Stories + scheduled posts
    |   |-- file_upload_handler.py # Handle files sent via Telegram
    |   |-- db_manager.py          # Database management
    |-- db/
    |   |-- setup_db.py            # One-command database setup
    |   |-- uct_agent.sqlite       # Local SQLite database
    |-- skills/                    # OpenClaw Node.js skills
    |-- info/                      # Team documentation
    |-- setup.sh                   # One-command session restore
    |-- post-to-instagram.sh       # Post image/video via URL
    |-- post-carousel.sh           # Post carousel
    |-- post-preview.sh            # Create preview draft
    |-- post-approve.sh            # Approve and publish draft
    |-- post-reject.sh             # Cancel draft
    |-- post-story.sh              # Post Instagram Story
    |-- post-analytics.sh          # Run analytics
    |-- generate-image.sh          # Generate AI image
    |-- dm-manager.sh              # Manage DMs and comments
    |-- scheduler.sh               # Schedule future posts
    |-- .env.example               # Environment variable template
    |-- package.json               # Node.js dependencies
    |-- README.md

---

## Bot Details

| Field | Value |
|---|---|
| Bot Name | UCT ClawGram |
| Bot Username | @uct_clawgram_bot |
| Instagram Account | @iot_academy_projects |
| Platform | Telegram Bot API via OpenClaw |
| Agent Brain | NVIDIA NIM z-ai/glm-5.2 (free) |

---

## Telegram Bot Commands

### General
| Command | Description |
|---|---|
| /start | Initialize the bot |
| /help | Show all commands |
| /status | Bot and Instagram account status |
| /cancel | Cancel current operation |

### Posting
| Command | Description |
|---|---|
| /post [url] [tone] | Post image with preview before posting |
| /carousel [url1,url2] [tone] | Post carousel with preview |
| /video [url] [tone] | Post video as Reel with preview |
| /generate [description] | Generate AI image and preview |

### File Upload (send directly via Telegram)
| Action | Description |
|---|---|
| Send a photo | Bot generates caption and shows preview |
| Send a video | Bot detects video and shows preview |
| Reply YES | Post to Instagram |
| Reply NO | Cancel and delete draft |

### Drafts
| Command | Description |
|---|---|
| /drafts | List pending drafts |
| /approve [id] | Approve and post a draft |
| /reject [id] | Cancel a draft |
| /clear_drafts | Delete all drafts |

### Analytics
| Command | Description |
|---|---|
| /analytics | Last 7 days performance |
| /analytics [N] | Last N days performance |
| /analytics [date1] [date2] | Custom date range |

### History & Storage
| Command | Description |
|---|---|
| /history | Last 10 posts |
| /storage | Database size and stats |
| /delete [id] | Delete a history entry |
| /clear_history | Clear all history |

### DMs & Comments
| Command | Description |
|---|---|
| /dms | Show DM inbox |
| /notify | Check for new DMs and notify |
| /comments [post_id] | Show comments on a post |
| /activity | AI summary of engagement |

### AI Router
| Command | Description |
|---|---|
| /ai_status | Show current AI provider |
| /ai_stats | Provider success rates |

---

## How It Works

    User sends message or file on Telegram
               |
               v
    OpenClaw receives (brain: NVIDIA NIM z-ai/glm-5.2)
               |
               v
    Claude reads skill and decides action
               |
               v
    Shell script triggers Python pipeline
               |
               v
    Multi-AI Router generates caption (NVIDIA/Cerebras/Mistral)
               |
               v
    Preview shown to user — waits for YES/NO
               |
               v
    On YES: Composio posts to Instagram
               |
               v
    Bot confirms with Post ID on Telegram

---

## Known Issues & Pending Work

### Vision Model Integration (Pending)
OpenClaw uses vision models to analyze images sent via Telegram before
generating captions. Currently the following vision models are configured
but failing due to API access issues:

- nvidia/meta/llama-3.2-11b-vision-instruct — timing out on NVIDIA NIM
- google/gemini-3-flash-preview — project access denied (403)
- anthropic/claude-opus-4-7 — no API key (intentionally removed)

**Impact:** When a user sends a photo directly, the bot cannot visually
analyze the image. It still posts successfully using a generically
generated caption, but the caption is not specific to the image content.

**Resolution plan:** Integrate NVIDIA Vision API with proper endpoint
configuration. This task is assigned to Abhishek and will be completed
in the upcoming development sprint.

**Workaround:** Users can add a description in their Telegram message
(e.g. "Post this sunset photo to Instagram") so the bot generates a
relevant caption without needing vision.

---

## End-to-End Testing Status

Full end-to-end testing of the complete Telegram-to-Instagram flow is
pending. Individual pipeline components have been verified working:

| Component | Tested | Status |
|---|---|---|
| Image posting via URL | Yes | Working |
| Carousel posting | Yes | Working |
| Video posting via URL | Yes | Working |
| AI caption generation | Yes | Working |
| Analytics dashboard | Yes | Working |
| DM reading + notifications | Yes | Working |
| AI image generation | Yes | Working |
| Story posting | Yes | Working |
| Scheduled posting | Yes | Working |
| File upload from Telegram | Yes | Posts working, vision pending |
| Preview flow (YES/NO) | Partial | Works via URL, vision issue affects file upload |

Full integration test with all components running simultaneously will
be completed as part of M11 open source release preparation.

---

## Session Restore (Lightning.ai)

Every new Lightning.ai session:

    cd ~/uct-insta-agent
    git pull origin main
    npm install -g openclaw
    bash setup.sh
    python3 db/setup_db.py
    # fill in .env with your API keys
    openclaw gateway run

---

## Contributors

| Name | Role | Contribution |
|---|---|---|
| Abhishek Kumar Shukla | Senior AI Developer | Project lead, all milestone implementations, Lightning.ai environment, Multi-AI Router, OpenClaw NVIDIA brain switch, file upload handler, vision API integration (upcoming) |
| Drupad Das | AI Developer | Co-developer, Windows local environment, milestone collaboration, code review |
| Manish | AI Developer | M5 video support architecture, auto content-type detection, reel/photo field integration |
| Raja | AI Developer | M6 analytics module research, content-type performance ranking methodology, explained OpenRouter-inspired multi-provider routing architecture used in ai_router.py |

---

## Milestone Clarification — M3 Pipeline Update vs M5

### M3 pipeline update (June 2026)
post-with-caption.py extended to auto-detect IMAGE vs VIDEO from
content-type headers. Video URLs post as Instagram Reels. AI caption
generation works for both. Contributed by Manish (video architecture)
and integrated by Abhishek.
Note: This is pipeline-level capability, NOT the full M5 milestone.

### M5 — full Telegram video UX (done via URL)
URL-based video posting confirmed working end-to-end from Telegram.
Direct phone file upload for video is included in the file upload
handler but vision analysis is pending (see Known Issues above).

---

## License

MIT — free to clone, modify, and self-host.

(c) 2026 Uniconverge Technologies Pvt. Ltd.
