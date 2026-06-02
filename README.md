# uct-insta-agent

AI-powered Instagram management via Telegram — built with OpenClaw,
Anthropic Claude, Composio MCP, and Google Gemini.

*Built by:* Uniconverge Technologies Pvt. Ltd.
*Website:* www.uniconvergetech.in

## Status
- [x] M1 — Environment setup & base agent
- [ ] M2 — Single image posting
- [ ] M3 — AI captions & scheduling
- [ ] M4 — Carousel / multi-image posts
- [ ] M5 — Single video posting
- [ ] M6 — Analytics dashboard
- [ ] M7 — Composio MCP — DMs & comments
- [ ] M8 — Gemini AI image generation
- [ ] M9 — Gemini AI short video generation
- [x] M10 — Stories & advanced scheduling
- [x] M11 — Open source packaging & docs

## Quick start
bash
git clone [https://github.com/uniconvergetech/uct-insta-agent](https://github.com/IOTAcademyAIProjects/uct-insta-agent)
cd uct-insta-agent
cp .env.example .env
# fill in your API keys in .env
npm install -g openclaw
openclaw start


## Requirements
- Node.js v18+
- Python 3.11 (for GPU pipelines — M8/M9 only)
- Lightning.ai 24 GB GPU Studio (M8/M9 only)
- Accounts: Telegram, Anthropic, Composio, Google AI Studio

## Tech stack
| Technology | Purpose |
|---|---|
| OpenClaw | Agent runtime & Telegram bot framework |
| Anthropic Claude | Reasoning, captions, hashtags, summaries |
| Composio MCP | Instagram publishing, DMs, comments, analytics |
| Google Gemini | AI image & short video generation |
| Lightning.ai | 24 GB GPU cloud studio for M8/M9 |
| Node.js v18+ | OpenClaw runtime environment |
| Python 3.11 | Gemini video & image pipelines |
| SQLite | Local draft post storage |

## Environment variables
Copy .env.example to .env and fill in your keys:
bash
cp .env.example .env


| Variable | Purpose | Source |
|---|---|---|
| ANTHROPIC_API_KEY | Claude API | console.anthropic.com |
| TELEGRAM_BOT_TOKEN | Telegram bot | @BotFather |
| COMPOSIO_CONSUMER_KEY | Composio MCP | dashboard.composio.dev |
| COMPOSIO_MCP_URL | Composio MCP server | connect.composio.dev/mcp |
| GOOGLE_GEMINI_API_KEY | Gemini image/video | aistudio.google.com |
| OPENCLAW_MODEL | Claude model | claude-sonnet-4-20250514 |
| GPU_ENABLED | Enable GPU pipelines | true / false |
| POST_TIMEZONE | Scheduled post timezone | e.g. Asia/Kolkata |

## Repository structure
```text
uct-insta-agent/
├── skills/
│   ├── instagram-post-image.js
│   ├── instagram-post-carousel.js
│   ├── instagram-post-video.js
│   ├── instagram-post-story.js
│   ├── caption-generator.js
│   ├── hashtag-researcher.js
│   ├── scheduler.js
│   ├── analytics-reporter.js
│   ├── composio-dm-handler.js
│   └── composio-comment-handler.js
├── pipelines/
│   ├── gemini-image-gen.py
│   ├── gemini-video-gen.py
│   └── ffmpeg-compress.py
├── lightning/
│   └── app.py
├── db/
│   └── drafts.sqlite
├── .github/workflows/
│   └── ci.yml
├── .env.example
├── openclaw.config.json
└── README.md
```

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit new skills via PR.

## License
MIT — free to clone, modify, and self-host.

© 2025 Uniconverge Technologies Pvt. Ltd.
