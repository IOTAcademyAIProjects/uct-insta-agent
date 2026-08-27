# ClawAgent v3.0 — Autonomous Social Media AI Operating System

**ClawAgent** is a multi-agent social media operating system designed to run on **$0/month free-tier AI APIs** while delivering enterprise-grade brand intelligence, multi-platform publishing, competitor monitoring, and content repurposing.

---

## Key Features

1. **Multi-Agent Specialist Architecture**:
   - 🎯 **Orchestrator Agent**: Fast intent routing using lightweight LLMs (~15 tokens/call).
   - 🎨 **Creator Agent**: High-converting, brand-voiced captions & A/B variant generation.
   - 👁️ **Vision Agent**: Multimodal visual analysis & visual tone extraction.
   - 📊 **Analyst Agent**: Performance metrics analysis & strategic growth recommendations.
   - 🔍 **Research Agent**: Competitor tracking, Google Trends synthesis, and weekly briefs.
   - 🖼️ **Designer Agent**: AI image generation calibrated to brand aesthetics.
   - 📤 **Publisher Agent**: Multi-platform publishing coordination across Instagram, LinkedIn, X, and YouTube.

2. **Hot-Swappable Model Stack (`config/models.yaml`)**:
   - Zero-downtime hot reloading of models, rate limits, and fallback chains.
   - Circuit breakers automatically isolate failing providers and restore them on recovery.
   - Supported free providers: Cerebras, NVIDIA NIM, Google Gemini Flash & Pro, Mistral AI, Pollinations AI, OpenRouter.
   - Optional paid upgrades: OpenAI, Banana.dev, Replicate.

3. **Persistent Brand Memory (`brands` Table & `BrandService`)**:
   - Learns your voice DNA (average sentence length, emoji frequency, hashtag patterns, top hooks) from past posts.
   - Enforces brand compliance (prohibited words, mandatory elements, visual moods).

4. **Human-in-the-Loop Previews**:
   - Review drafts, edit captions, and approve before live publishing.

---

## Quick Start

### 1. Install Dependencies
```bash
bash setup.sh
```

### 2. Configure Environment
Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
```

### 3. Verify Model Health
```bash
python cli.py ai-status
```

---

## CLI Command Reference

| Action | Command |
|---|---|
| **Direct Post** | `python cli.py post <image_url> --tone casual --platforms instagram` |
| **Carousel Post** | `python cli.py carousel "url1,url2,url3" --tone casual` |
| **Generate AI Image** | `python cli.py generate "futuristic city in cyber aesthetic"` |
| **Create Draft Preview** | `python cli.py preview <image_url> --tone inspirational` |
| **Approve Draft** | `python cli.py approve <draft_id>` |
| **Reject Draft** | `python cli.py reject <draft_id>` |
| **Update Caption** | `python cli.py update <draft_id> "Brand new caption"` |
| **Performance Analytics** | `python cli.py analytics --days 7` |
| **Brand Management** | `python cli.py brand list` / `python cli.py brand switch <name>` |
| **Extract Brand Voice** | `python cli.py brand analyze` |
| **Competitor Brief** | `python cli.py competitors` / `python cli.py competitors --add @handle` |
| **Niche Trends** | `python cli.py trends` |
| **Weekly Content Brief** | `python cli.py ideas` |
| **Content Repurposing** | `python cli.py repurpose "Long form article text or file.txt"` |
| **DB Storage Stats** | `python cli.py db storage` |

---

## Project Structure

```
UCT_ag/
├── config/
│   ├── models.yaml          # Hot-swappable model stack configuration
│   └── platforms.yaml       # Platform adapter configuration
├── core/
│   ├── model_router.py      # Task-based routing & fallback chains
│   ├── circuit_breaker.py   # Circuit breaker state machine
│   ├── config_loader.py     # YAML loader & watchdog hot-reload
│   └── exceptions.py        # Custom exceptions
├── providers/               # Provider client implementations
│   ├── base.py
│   ├── openai_compatible.py # NVIDIA NIM, Cerebras, Mistral, Ollama, OpenAI
│   ├── google_genai.py      # Gemini Flash, Gemini Pro
│   ├── pollinations.py      # Free image generation
│   ├── replicate_provider.py
│   └── banana_provider.py
├── agents/                  # Specialist agent pool
│   ├── orchestrator.py
│   ├── creator_agent.py
│   ├── vision_agent.py
│   ├── analyst_agent.py
│   ├── research_agent.py
│   ├── designer_agent.py
│   ├── scheduler_agent.py
│   └── publisher_agent.py
├── adapters/                # Social media platform adapters
│   ├── base.py
│   ├── instagram.py
│   ├── linkedin.py
│   ├── twitter.py
│   └── youtube.py
├── services/                # Business logic services
│   ├── brand_service.py
│   ├── draft_service.py
│   ├── media_host.py
│   ├── scheduler_service.py
│   ├── engagement_service.py
│   ├── trend_service.py
│   ├── competitor_service.py
│   ├── repurpose_service.py
│   └── db_service.py
├── db/
│   ├── setup_db.py          # SQLite DDL (13 tables)
│   ├── migrate.py           # Database migration utility
│   ├── repository.py        # Central database access layer
│   └── uct_agent.sqlite     # SQLite database
├── prompts/                 # Brand-aware prompt templates
├── pipelines/               # Backward-compatible wrappers
├── cli.py                   # Unified CLI entrypoint
├── setup.sh                 # Environment setup script
├── requirements.txt         # Pinned dependencies
├── PRD.md                   # Product Requirement Document v3.0
└── SPEC_SHEET.md            # Technical Specification Sheet v3.0
```

---

## License
MIT License. Developed by Swarit Sharma / Uniconverge Technologies Pvt. Ltd.
