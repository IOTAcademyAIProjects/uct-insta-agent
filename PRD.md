# Product Requirement Document — ClawAgent v3.0

**Codename:** ClawAgent  
**Document Version:** 3.1.0  
**Status:** Architecture Blueprint — Self-Improving Loop  
**Author:** Swarit Sharma / Uniconverge Technologies Pvt. Ltd.  
**Last Updated:** 2026-08-28  

---

## Part I — Why This Exists

### 1.1 The Real Problem

Every creator, freelancer, agency, and small business faces the same trap:

1. **Tool Sprawl & Cost Creep.** Buffer ($6/mo/channel), Hootsuite ($99/mo), Later ($25/mo), Sprout Social ($249/mo). Managing 4 platforms across 2 brands? That's $200-$1000/month _before_ you've created a single piece of content.

2. **AI Is Disconnected From Publishing.** ChatGPT writes captions. Canva makes images. Buffer schedules posts. Analytics lives in Meta Business Suite. None of them talk to each other. The human is the glue.

3. **"One Brain" Agents Break.** Existing AI agents use a single LLM for everything — the same model that writes your caption also tries to analyze your competitor's engagement funnel. It's like hiring one person to be your copywriter, data analyst, graphic designer, and strategist simultaneously.

4. **Brand Amnesia.** Every session starts from zero. The AI doesn't remember your color palette, your audience's vocabulary, your past top-performing hooks, or that your brand never uses exclamation marks.

### 1.2 What ClawAgent Is

ClawAgent is a **multi-agent social media operating system** — not a single chatbot. It's a team of specialized AI workers, each expert in one domain, coordinated by an orchestrator, operated through a Telegram chat (and later, a web dashboard).

**Core design principles:**

| Principle | What It Means In Practice |
|---|---|
| **Cost = $0 by default** | Every capability works on free-tier providers. Paid keys are optional upgrades, never requirements. |
| **Specialize, Don't Generalize** | A vision model describes images. A creative model writes captions. A reasoning model analyzes competitors. A fast model formats JSON. Each task goes to the right brain. |
| **Memory Is Non-Negotiable** | The agent remembers your brand voice, your top hooks, your color palette, your audience segments, and your posting history — across sessions, forever. |
| **Diverse Users, One System** | A solo food blogger in Jaipur and a 50-person marketing agency in Bangalore use the same system. Configuration, not code, determines the experience. |
| **Human-in-the-Loop, Not Human-in-the-Way** | Every destructive action requires approval. Every informational action is instant. |

---

## Part II — User Personas & Their Workflows

### Persona 1: Solo Creator (Priya, Food Blogger, Jaipur)
- **Platforms:** Instagram, YouTube Shorts  
- **Budget:** ₹0/month for tools  
- **Pain:** Spends 2 hours daily writing captions, editing photos, thinking of what to post  
- **Wants:** "I send a food photo on Telegram, the bot writes a caption _in my style_, I say YES, it posts. Done in 30 seconds."

### Persona 2: Freelance Social Media Manager (Arjun, manages 4 client brands)
- **Platforms:** Instagram, LinkedIn, X/Twitter per client  
- **Budget:** Clients pay ₹5000/month each; tools eat into margin  
- **Pain:** Context-switching between 4 brand voices, 3 platforms, and 5 analytics dashboards  
- **Wants:** "Switch brand context with one command. The bot knows each client's voice, color rules, and posting schedule."

### Persona 3: D2C Startup Marketing Team (BrandX, 3 people)
- **Platforms:** Instagram, LinkedIn, YouTube  
- **Budget:** ₹2000/month for AI tools  
- **Pain:** No one has time to research what competitors are doing or what trends to jump on  
- **Wants:** "Every Monday the bot tells us what our top 3 competitors posted last week, what's trending in our niche, and gives us 5 content ideas with draft captions."

### Persona 4: Marketing Agency (CreativeHive, 15 employees, 20 brands)
- **Platforms:** All major platforms  
- **Budget:** ₹10000/month for AI tools  
- **Pain:** Approval workflows, brand compliance, consistent quality across 20 different brand identities  
- **Wants:** "Junior team members create drafts. The bot checks brand compliance automatically. Senior managers approve via Telegram inline buttons."

---

## Part III — Feature Architecture

### 3.1 Multi-Agent Orchestration (The Core Innovation)

Instead of one monolithic LLM call, ClawAgent uses **specialized sub-agents** coordinated by an **Orchestrator**:

```
User Message
    │
    ▼
┌─────────────────────┐
│  ORCHESTRATOR AGENT  │ ← Classifies intent, routes to specialist
│  (Fast LLM: Cerebras│
│   or Gemini Flash)   │
└─────┬───────────────┘
      │
      ├──► 🎨 Creator Agent      — Writes captions, generates image prompts
      ├──► 👁️ Vision Agent        — Describes uploaded images/videos
      ├──► 📊 Analyst Agent       — Runs analytics, interprets data
      ├──► 🔍 Research Agent      — Monitors competitors, finds trends
      ├──► 🖼️ Designer Agent      — Generates images via diffusion models
      ├──► 📅 Scheduler Agent     — Manages calendar, finds optimal post times
      └──► 📤 Publisher Agent     — Handles platform APIs, format adaptation
```

**Why this matters for cost:**
- The Orchestrator uses the cheapest/fastest model (Cerebras at 1M free tokens/day) to classify intent — this is a 20-token task.
- Only the specialist agent fires the expensive model, and only for its narrow domain.
- Vision tasks don't waste creative model tokens. Analytics don't waste image generation credits.

### 3.2 Platform Adapters

| Platform | Publishing API | Content Types | Free Tier Reality |
|---|---|---|---|
| **Instagram** | Composio MCP / IG Graph API | Feed (1:1, 4:5), Reels (9:16), Stories, Carousels | Composio free tier: 1000 actions/month |
| **LinkedIn** | LinkedIn Marketing API v2 | Text posts, Single image, Document carousels, Articles | API access: free with approved app |
| **X / Twitter** | X API v2 (Free tier) | Tweets (280 chars), Threads, Image tweets | Free tier: 1500 tweets/month |
| **YouTube** | YouTube Data API v3 | Shorts (< 60s vertical video) | 10,000 units/day free |
| **Facebook** | Meta Graph API | Feed posts, Stories, Reels | Shared with Instagram Business |
| **Threads** | Threads API | Text posts, Image posts | Free with IG Business |

**Adapter contract:** Each adapter implements a standard interface:

```python
class PlatformAdapter(Protocol):
    def validate_content(self, payload) -> ValidationResult
    def format_media(self, media, target_spec) -> FormattedMedia
    def publish(self, content) -> PublishResult
    def get_analytics(self, date_range) -> AnalyticsData
    def get_engagement(self) -> EngagementData
```

### 3.3 Brand Memory System

This is the feature that transforms the agent from "generic AI tool" to "my social media team member who knows my brand."

**Layer 1 — Brand Identity Profile (Explicit)**
User explicitly defines or the system extracts from existing content:
- Color palette hex codes
- Typography preferences (serif vs sans-serif, formal vs playful)
- Logo placement rules
- Prohibited words/phrases ("Don't ever say 'synergy' or 'leverage'")
- Mandatory elements ("Always end with a question to drive comments")

**Layer 2 — Voice DNA (Learned)**
Automatically analyzed from the user's last 50 posts:
- Average sentence length
- Emoji frequency and type distribution
- Hashtag patterns (count, position, branded vs generic)
- Hook structures (question openers vs statement openers vs emoji openers)
- Call-to-action style

**Layer 3 — Performance Memory (Continuous)**
After every post, the system logs what worked:
- Which hooks got the highest engagement rate?
- Which hashtag combinations drove the most reach?
- What posting times generated the best initial velocity?
- Which content themes resonated (travel > food > behind-the-scenes)?

**All three layers are injected into every generation prompt as system context**, so the AI writes _as your brand_, not as a generic assistant.

### 3.4 Hot-Swappable Model Stack

**The problem with v1:** Providers are hardcoded in a Python list. Adding Gemini means editing `ai_router.py`, restarting the process, and hoping nothing breaks.

**The v3 solution:** A declarative `models.yaml` config with file-watcher hot-reload:

```yaml
# config/models.yaml — Edit this file. Changes take effect in < 5 seconds.
version: 3
defaults:
  text: cerebras         # Cheapest for orchestration
  creative: nvidia       # Best free creative writing
  vision: gemini_flash   # Best free multimodal
  image: pollinations    # No API key needed
  reasoning: mistral     # Deep analysis

providers:
  cerebras:
    type: openai_compatible
    base_url: https://api.cerebras.ai/v1
    api_key_env: CEREBRAS_API_KEY
    model: gpt-oss-120b
    capabilities: [text, fast_formatting]
    cost_tier: free
    rate_limit: 1000000_tokens_per_day

  nvidia:
    type: openai_compatible
    base_url: https://integrate.api.nvidia.com/v1
    api_key_env: NVIDIA_API_KEY
    model: z-ai/glm-5.2
    capabilities: [text, creative_writing]
    cost_tier: free
    rate_limit: 40_rpm

  gemini_flash:
    type: google_genai
    api_key_env: GEMINI_API_KEY
    model: gemini-2.5-flash
    capabilities: [text, vision, reasoning, creative_writing]
    cost_tier: free  # 1500 RPD free tier
    rate_limit: 1500_rpd

  gemini_pro:
    type: google_genai
    api_key_env: GEMINI_API_KEY
    model: gemini-2.5-pro
    capabilities: [reasoning, deep_analysis]
    cost_tier: free  # 25 RPD free tier
    rate_limit: 25_rpd

  mistral:
    type: openai_compatible
    base_url: https://api.mistral.ai/v1
    api_key_env: MISTRAL_API_KEY
    model: mistral-large-latest
    capabilities: [text, creative_writing, reasoning]
    cost_tier: free

  pollinations:
    type: pollinations
    model: flux
    capabilities: [image_generation]
    cost_tier: free
    rate_limit: unlimited

  # --- OPTIONAL PAID UPGRADES (user adds these if they want) ---
  banana_dev:
    type: banana
    api_key_env: BANANA_API_KEY
    model: flux-1-dev
    capabilities: [image_generation]
    cost_tier: paid
    enabled: false  # User enables when ready

  openai:
    type: openai
    api_key_env: OPENAI_API_KEY
    model: gpt-4o-mini
    capabilities: [text, vision, creative_writing, reasoning]
    cost_tier: paid
    enabled: false

  replicate:
    type: replicate
    api_key_env: REPLICATE_API_TOKEN
    model: black-forest-labs/flux-schnell
    capabilities: [image_generation]
    cost_tier: paid
    enabled: false

fallback_chains:
  text: [cerebras, nvidia, mistral, gemini_flash]
  creative: [nvidia, mistral, gemini_flash, cerebras]
  vision: [gemini_flash, openai]
  image: [pollinations, banana_dev, replicate]
  reasoning: [mistral, gemini_pro, gemini_flash]
```

**Hot-reload mechanism:**
- A Python `watchdog` file observer monitors `config/models.yaml`.
- On any write, the model registry rebuilds in-memory within 3 seconds.
- Active in-flight requests complete on the old config. New requests use the new config.
- No process restart. No downtime. No code changes.

### 3.5 Intelligent Task-Based Model Routing

The v1 round-robin treats every task identically. v3 routes based on **what the task actually needs**:

| Task Type | What It Needs | Why a Specific Model | Default Free Provider |
|---|---|---|---|
| **Intent Classification** | Speed, low cost (10-20 tokens) | This runs on every single message; must be near-free | Cerebras (1M tokens/day free) |
| **Caption Writing** | Creativity, brand voice adherence | Needs strong instruction-following and style mimicry | NVIDIA NIM (40 RPM free) |
| **Image Description** | Multimodal vision | Must _see_ the image to describe it accurately | Gemini 2.5 Flash (1500 RPD free) |
| **Analytics Summary** | Reasoning over structured data | Must interpret numbers, rank, and generate insights | Mistral Large |
| **Competitor Analysis** | Deep reasoning + web research | Complex multi-step reasoning with large context | Gemini 2.5 Pro (25 RPD free) |
| **Content Ideation** | Creativity + trend awareness | Needs to be inventive, not just summarize | NVIDIA NIM or Mistral |
| **JSON/Format Tasks** | Speed, structured output | Formatting platform payloads, parsing API responses | Cerebras (fastest free model) |
| **Image Generation** | Diffusion model | Text-to-image synthesis | Pollinations (unlimited, free) |

**Routing logic pseudocode:**

```python
def route_task(task_type: str, models_config: dict) -> Provider:
    # 1. Get the default provider for this task type
    default = models_config['defaults'].get(task_type)
    
    # 2. Build fallback chain from config
    chain = models_config['fallback_chains'].get(task_type, [])
    
    # 3. Filter to only enabled providers with required capability
    available = [p for p in chain 
                 if models_config['providers'][p]['enabled'] 
                 and not is_circuit_open(p)]
    
    # 4. Return first available, or raise
    if available:
        return available[0]
    raise AllProvidersExhausted(task_type)
```

### 3.6 Competitor & Trend Intelligence

**Competitor Monitoring Pipeline:**

1. User registers competitor handles: `/competitor add @competitor_handle instagram`
2. System periodically fetches their public post data (caption text, post type, approximate engagement)
3. AI Analyst Agent generates a weekly digest:
   - What topics are they posting about that you're not?
   - What's their most engaging content format?
   - What hooks and CTAs are they using?
   - Engagement rate comparison (your avg vs theirs)

**Trend Detection Pipeline:**

1. Google Trends API (free) — top rising queries in user's niche
2. Instagram hashtag volume trends (via public endpoints)
3. X/Twitter trending topics filtered by relevance
4. AI synthesizes these into **5 actionable content ideas** with draft captions and suggested visuals

**Weekly Strategy Brief** (Telegram message every Monday 9 AM):
```
📊 Weekly Content Intelligence — Week 35

🔥 Trending in your niche:
  1. "AI-powered home automation" (+340% search volume)
  2. "Smart kitchen gadgets 2026" (trending on X)
  3. Audio trend: [specific trending audio] (Instagram Reels)

👀 Competitor spotlight (@competitor_brand):
  - Posted 12 times (you posted 5)
  - Their top post: carousel about "5 mistakes..." (4.2% engagement)
  - They're covering "sustainability" — you haven't touched it

💡 Content ideas for this week:
  1. Carousel: "5 AI home gadgets under ₹5000" — tap into trending search
  2. Reel: React to [trending audio] with your product demo
  3. LinkedIn post: "Why we chose sustainable packaging" — fill competitor gap
  4. Story poll: "Which feature should we build next?" — engagement driver
  5. Thread (X): "The future of smart homes in India — a thread 🧵"
```

### 3.7 Content Repurposing Engine

One piece of content should become many:

```
User writes a LinkedIn article (800 words)
    │
    ├──► Extract 5 key insights → 5 Twitter/X thread tweets
    ├──► Summarize to 3 paragraphs → Instagram carousel (text-on-image slides)
    ├──► Pull best quote → Single Instagram post with branded quote card
    ├──► Generate 30-second talking points → YouTube Shorts script
    └──► Create poll from article's main question → Instagram Story poll
```

The user creates once. The agent distributes everywhere.

### 3.8 A/B Caption Testing

For users who want data-driven optimization:

1. Agent generates 2-3 caption variants for the same image
2. User picks or the system randomly selects one to post
3. After 48 hours, system logs the engagement data
4. Over time, the Performance Memory learns which caption patterns perform best for this specific audience
5. Future captions are biased toward proven patterns

### 3.9 Smart Scheduling with Audience Intelligence

Instead of "post at 9 AM because a blog said so":

1. Analyze the user's last 90 days of post data
2. Map engagement velocity (likes in first hour) against posting time
3. Identify the user's _specific audience's_ active windows
4. Automatically suggest optimal posting slots per platform
5. The scheduler fills these slots with queued content

### 3.10 Interactive Telegram UX

Replace text commands with inline keyboard buttons:

```
🖼️ Draft Preview #47

Caption: "The future of sustainable tech is here... 🌿"
Platform: Instagram (Feed) + LinkedIn
Tone: Professional | Brand: BrandX

[✅ Approve & Post]  [✏️ Edit Caption]
[🎨 Regenerate Image] [🔄 Change Tone]
[⏰ Schedule for Later] [❌ Discard]
```

### 3.11 Multi-Brand / Multi-Tenant Support

For freelancers and agencies managing multiple brands:

- `/brand switch BrandX` — switches all generation context (voice, colors, platform accounts, analytics)
- Each brand has isolated: brand profile, posting history, analytics, draft queue, scheduled posts
- One Telegram bot instance, many brand contexts

### 3.12 Accessibility & Inclusive Content

- **Auto alt-text generation:** Every image post gets AI-generated alt text for screen readers
- **Color contrast checking:** Generated images are validated for WCAG AA contrast compliance
- **Caption readability scoring:** Flesch-Kincaid grade level shown in preview
- **Multi-language support:** Captions generated in user's preferred language with cultural adaptation (not just translation)

### 3.13 Self-Improving Loop (Observe → Hypothesize → Propose → Approve → Measure)

**Why it exists:** Static brand memory rots. The agent must learn from its own outcomes and competitor shifts without drifting or hallucinating brand voice. All changes are proposed as dry-run, human-approved, and measured with auto-revert.

**Loop overview (1 proposal / brand / week cap):**
```
Observe (14d posts, trends, competitor gaps, ai_calls latency)
   ↓
Hypothesize (LLM reasoning OR heuristic fallback) → ONE field change
   ↓
Propose (improvement_log status=PROPOSED, dry_run=1) → Telegram card
   ↓
Human Approve/Reject (Telegram [✅ Apply] [❌ Reject] or CLI/API)
   ↓
Apply (BrandService.update_profile → brands.hashtag_count_range / sample_hooks / avg_sentence_length)
   ↓
Measure after 7d (compare metric_before vs metric_after engagement_rate)
   ↓
Keep (MEASURED) or Auto-Revert (REVERTED) if lift < -5%
```

**L1 Safe (auto-proposable, human gate):**
- `hashtag_count_range` (e.g. "5-7" → "1-3" when winners avg 1.2 tags)
- `sample_hooks` (refresh top 3 winner openers)
- `avg_sentence_length` / `emoji_frequency` (align to winner readability)

**L3 Gated (never auto, manual review only):** `tone_of_voice, prohibited_words, mandatory_elements` — rejected if LLM proposes.

**Telegram UX:**
```
🧬 Self-Improvement Proposal #12 — BrandX | PROPOSED
Type: L1_HASHTAG | Field: hashtag_count_range
From: 5-7 → To: 1-3
Hypothesis: Top 5 avg 1.2 tags vs brand 5-7, bottom 6.1; tightening lifts 15%
Predicted: 15% | Baseline: 3.76%
[✅ Apply Insight] [❌ Reject]  [📊 View Details] [📈 History]
```

**CLI:**
```bash
python cli.py improve propose          # dry-run propose
python cli.py improve list             # pending
python cli.py improve approve 12       # apply
python cli.py improve measure 12       # compare 7d
python cli.py improve history          # audit
```

**Safety & Cost:**
- $0 — uses `reasoning` free chain `mistral → gemini_pro` `config/models.yaml:152` or heuristic fallback when no keys.
- Allowlist `openclaw-config/openclaw.json:allowFrom` + `core/security.py:sanitize_user_input` + `mask_secrets` for logs `improvement_log` `db/setup_db.py:220`.
- Single weekly cap + dry-run default prevents drift; L3 gated.
- Every hypothesis logged to `improvement_log` for leader audit.

---

## Part IV — Cost Architecture

### Default Free Stack (₹0/month)

| Component | Free Provider | Free Tier Limit | Estimated Monthly Usage |
|---|---|---|---|
| Intent Classification | Cerebras | 1M tokens/day | ~50K tokens/month (well within) |
| Caption Generation | NVIDIA NIM | 40 RPM, 1000 credits | ~100 captions/month |
| Vision / Image Description | Gemini 2.5 Flash | 1500 req/day | ~100 images/month |
| Deep Reasoning / Strategy | Mistral Large | ~1B tokens/month | ~20 analyses/month |
| Competitor Analysis | Gemini 2.5 Pro | 25 req/day | ~4 weekly briefs |
| Image Generation | Pollinations AI | Unlimited | ~100 images/month |
| Image Hosting | imgbb | Unlimited (free tier) | ~200 uploads/month |
| Instagram API | Composio Free | 1000 actions/month | ~150 posts/month |
| Database | SQLite (local) | Unlimited | N/A |

**Total monthly cost: ₹0**

### Optional Paid Upgrades

| Upgrade | What It Unlocks | Cost |
|---|---|---|
| Gemini API (pay-as-you-go) | Higher rate limits, longer context | ~$0.01-0.05/1K tokens |
| Banana.dev / Replicate | Higher-quality image generation (FLUX.1-dev) | ~$0.01-0.05/image |
| OpenAI GPT-4o-mini | Premium vision + creative writing | ~$0.15/M input tokens |
| Cloudinary (free tier) | Better CDN + image transformation | Free up to 25K transforms/month |
| Redis Cloud (free tier) | Distributed job queue for teams | Free up to 30MB |

---

## Part V — Security & Privacy

- **Credential Isolation:** All API keys stored in `.env` or encrypted `config/secrets.enc`. Never committed to git. Never logged.
- **OAuth Token Refresh:** Platform tokens (Instagram, LinkedIn, X) auto-refreshed before expiry.
- **Telegram Allowlist:** Bot only responds to allowlisted Telegram user IDs (configured in OpenClaw).
- **Local-First Data:** All post history, brand profiles, and analytics stored in local SQLite. No cloud telemetry unless explicitly opted in.
- **Prompt Injection Defense:** User-supplied content (captions, descriptions) is sandboxed in prompt templates and never injected into system prompts directly.

---

## Part VI — Success Metrics

| Metric | Target | Measurement |
|---|---|---|
| Time from "photo taken" to "posted on Instagram" | < 60 seconds | Timestamp delta: file upload → publish confirmation |
| Caption brand-voice consistency | > 85% match score | Cosine similarity between generated caption embedding and brand voice vector |
| Provider availability | > 99.5% | Circuit breaker logs: successful calls / total calls |
| User monthly cost | ₹0 for solo creators | Sum of all API charges |
| Content ideas acted upon | > 30% of suggestions | Ratio of trend suggestions that become published posts |
| Self-improvement lift | > 10% engagement delta kept, <5% false apply | `improvement_log` `metric_before → metric_after` KEEP/REVERT rate |

---

## Part VII — Milestone Roadmap (v3.0)

| Phase | Milestone | Features | Timeline |
|---|---|---|---|
| **Phase 1** | Foundation Upgrade | Hot-swap model config, task-based routing, Gemini integration, circuit breakers | Week 1-3 |
| **Phase 2** | Brand Memory | Brand DNA extraction, voice profiling, performance memory, prompt injection | Week 4-6 |
| **Phase 3** | Multi-Platform | LinkedIn adapter, X/Twitter adapter, platform format engine, cross-posting | Week 7-10 |
| **Phase 4** | Intelligence | Competitor monitoring, trend detection, weekly strategy briefs, content ideation | Week 11-14 |
| **Phase 5** | Advanced UX | Telegram inline keyboards, multi-brand switching, A/B testing, content repurposing | Week 15-18 |
| **Phase 6** | Scale & Polish | Redis queue, web dashboard (optional), agency multi-tenant, documentation | Week 19-22 |
| **Phase 7** | Self-Improving Loop | Observe→Hypothesize→Propose→Approve→Measure, improvement_log, L1 safe + L3 gated, auto-revert, leader audit | Week 23-24 |
