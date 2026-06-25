# uct-insta-agent

AI-powered Instagram management via Telegram — built with OpenClaw, Anthropic Claude, Composio MCP, and Google Gemini.

**Built by:** Uniconverge Technologies Pvt. Ltd.
**Website:** www.uniconvergetech.in

---

## Milestone Progress

| # | Milestone | Status |
|---|---|---|
| M1 | Environment setup & base agent | ✅ Done |
| M2 | Single image posting | ✅ Done |
| M3 | AI captions & scheduling | ✅ Done |
| M4 | Carousel / multi-image posts | ⏳ Pending |
| M5 | Single video posting — full Telegram UX | ⏳ Pending |
| M6 | Analytics dashboard | ⏳ Pending |
| M7 | Composio MCP — DMs & comments | ⏳ Pending |
| M8 | Gemini AI image generation | ⏳ Pending |
| M9 | Gemini AI short video generation | ⏳ Pending |
| M10 | Stories & advanced scheduling | ⏳ Pending |
| M11 | Open source packaging & docs | ⏳ Pending |

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
| Anthropic Claude | Reasoning, captions, hashtags, summaries |
| Composio MCP | Instagram publishing, DMs, comments, analytics |
| Google Gemini | AI image & short video generation (M8/M9) |
| imgbb | Free image hosting — public URLs for Instagram API |
| Lightning.ai | 24GB GPU cloud studio for M8/M9 |
| Node.js v18+ | OpenClaw runtime environment |
| Python 3.11 | Image/video pipelines |
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
    ├── skills/
    │   ├── instagram-post-image.js    # Image posting skill
    │   └── caption-generator.js       # Caption generation skill
    ├── pipelines/
    │   └── post-with-caption.py       # IMAGE + VIDEO posting pipeline
    ├── lightning/
    │   └── app.py                     # Lightning.ai entry point
    ├── db/
    │   └── drafts.sqlite              # Local draft storage
    ├── info/
    │   ├── openclawsetup.md           # OpenClaw setup guide
    │   └── telegramsetup.md           # Telegram bot pairing guide
    ├── openclaw-config/
    │   └── openclaw.example.json      # Config reference
    ├── .github/workflows/
    │   └── ci.yml                     # GitHub Actions CI
    ├── setup.sh                       # One-command session restore
    ├── post-to-instagram.sh           # Shell bridge for OpenClaw skill
    ├── test-m2.py                     # M2 image posting test
    ├── test-imgbb.py                  # imgbb upload test
    ├── .env.example                   # Environment variable template
    ├── package.json                   # Node.js dependencies
    └── README.md

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
    Claude generates caption + hashtags
               |
               v
    imgbb hosts the image (public URL)
               |
               v
    Composio posts to Instagram via Meta API
               |
               v
    Bot confirms with Post ID on Telegram

---

## Milestone Clarification — M3 Pipeline Update vs M5

### What was completed in M3 pipeline update (June 2026)

The post-with-caption.py pipeline was extended with video support:

- Auto-detects IMAGE vs VIDEO from HTTP content-type headers
- Video URLs are posted as Instagram Reels via Composio
- Image URLs are uploaded to imgbb then posted as photos
- AI caption generation via Claude works for both image and video
- content_type field correctly set — reel for video, photo for image

NOTE: This is a pipeline-level capability update, NOT the full M5 milestone.
Credit: Video architecture contributed by Manish, integrated with Claude by Abhishek.

### What M5 will deliver (pending)

M5 is the full Telegram-to-Instagram video UX milestone:

- User sends an MP4 file directly via Telegram to @uct_clawgram_bot
- Bot handles Telegram file size limits (20MB max via Bot API)
- Large file chunking for videos above the Telegram limit
- User chooses Reel or Feed video before posting
- Claude generates video caption and cover thumbnail suggestion
- Account capability check before submission
- Confirmation with Instagram post URL and estimated reach
- Proper error handling for unsupported video formats and durations

NOTE: M5 is still pending and has not been started.

---

## Contributors

| Name | Role | Contribution |
|---|---|---|
| Abhishek Kumar Shukla | Senior AI Developer | Project lead, Lightning.ai environment, M1 OpenClaw setup, M2 Composio integration, M3 Claude caption pipeline, Telegram bot wiring, overall architecture |
| Drupad Das | AI Developer | Co-developer, Windows local environment, milestone collaboration, code review |
| Manish | AI Developer | Video support architecture — auto content-type detection (IMAGE vs VIDEO), video URL handling, content_type field (reel/photo) integrated into post-with-caption.py |

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

- Never commit .env — it is in .gitignore
- Rotate all tokens before M11 public release
- Bot DM policy is set to allowlist — only approved Telegram IDs can interact
- Run openclaw security audit regularly

---

## License

MIT — free to clone, modify, and self-host.

© 2025 Uniconverge Technologies Pvt. Ltd.
