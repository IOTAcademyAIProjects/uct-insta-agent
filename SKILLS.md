# uct-insta-agent — Skills Reference

This document describes every OpenClaw skill in the project — what triggers it, what it does, and how to customize it.

---

## What is an OpenClaw Skill?

A skill is a Markdown file with YAML frontmatter that tells the OpenClaw agent what to do in certain situations. Skills live in `~/.openclaw/workspace/skills/SKILL_NAME/SKILL.md`. The agent brain reads the skill description and decides when to call it based on what the user says.

---

## Skill Files Location

```
~/.openclaw/workspace/skills/
├── instagram-post/SKILL.md
├── instagram-carousel/SKILL.md
├── instagram-analytics/SKILL.md
├── instagram-dm/SKILL.md
├── instagram-generate/SKILL.md
├── instagram-file-upload/SKILL.md
└── db-manager/SKILL.md
```

---

## Skill 1 — instagram-post

**Triggers when:** User wants to post a single image or video to Instagram via a URL.

**Example user messages:**
- "Post this to Instagram: https://example.com/image.jpg"
- "Share this photo on Instagram with inspirational tone"
- "/post https://example.com/image.jpg casual"

**What it does:**
1. Calls `~/post-preview.sh URL TONE`
2. Uploads image to imgbb
3. Generates caption via Multi-AI Router
4. Saves as PENDING draft in SQLite
5. Shows preview to user (caption + image URL)
6. Waits for YES or NO
7. On YES: calls `~/post-approve.sh DRAFT_ID` → posts to Instagram
8. On NO: calls `~/post-reject.sh DRAFT_ID` → deletes draft

**Supported tones:** casual, inspirational, professional, funny

---

## Skill 2 — instagram-carousel

**Triggers when:** User wants to post multiple images as a single swipeable carousel.

**Example user messages:**
- "Post these as a carousel: url1, url2, url3"
- "Create a carousel with these images"
- "/carousel url1,url2 inspirational"

**What it does:**
1. Accepts 2-10 comma-separated image URLs
2. Uploads each to imgbb individually
3. Creates child containers via `INSTAGRAM_CREATE_MEDIA_CONTAINER` with `is_carousel_item: true`
4. Creates carousel container via `INSTAGRAM_CREATE_CAROUSEL_CONTAINER`
5. Publishes via `INSTAGRAM_CREATE_POST`
6. Generates one unified Claude caption for the whole carousel

**Minimum images:** 2
**Maximum images:** 10

---

## Skill 3 — instagram-analytics

**Triggers when:** User asks about Instagram performance, stats, engagement, or analytics.

**Example user messages:**
- "How are my posts doing?"
- "Show me analytics for last 30 days"
- "Which type of content works best?"
- "/analytics 2026-06-01 2026-06-30"

**What it does:**
1. Fetches recent posts via `INSTAGRAM_GET_IG_USER_MEDIA`
2. Filters by date range (default: last 7 days)
3. Fetches insights per post via `INSTAGRAM_GET_IG_MEDIA_INSIGHTS`
4. Ranks content types by average engagement (IMAGE vs VIDEO vs CAROUSEL)
5. Generates plain-English summary via Multi-AI Router

**Usage modes:**
- `~/post-analytics.sh` — last 7 days
- `~/post-analytics.sh 30` — last 30 days
- `~/post-analytics.sh 2026-06-01 2026-06-30` — custom range

---

## Skill 4 — instagram-dm

**Triggers when:** User asks about DMs, comments, engagement, or inbox.

**Example user messages:**
- "Show my DMs"
- "Any new messages?"
- "Check comments on my posts"
- "/notify"
- "Summarize my Instagram engagement"

**What it does:**
- `dms` — lists DM conversations from inbox
- `notify` — checks for new DMs and sends Telegram notification
- `conversation ID` — reads full message thread
- `comments POST_ID` — shows comments on a specific post
- `replies COMMENT_ID` — shows replies to a comment
- `delete COMMENT_ID` — deletes a comment
- `summary` — AI summary of all recent engagement activity

**Telegram notifications:** When `notify` runs, new DMs trigger a Telegram message to the owner. Already-seen DMs are tracked in `db/uct_agent.sqlite` (seen_dms table) to avoid duplicate notifications.

---

## Skill 5 — instagram-generate

**Triggers when:** User wants to generate an AI image from a text description.

**Example user messages:**
- "Generate an image of a futuristic Indian city at night"
- "Create an AI image of mountains at sunset"
- "/generate a cat wearing sunglasses on a beach"

**What it does:**
1. Calls `~/generate-image.sh DESCRIPTION TONE`
2. Sends prompt to Pollinations AI (free, no API key needed)
3. Downloads generated image (typically 60-150KB)
4. Uploads to imgbb for permanent URL
5. Generates Instagram caption via Multi-AI Router
6. Saves as PENDING draft
7. Shows preview to user
8. On YES: posts to Instagram

**Image generation model:** Pollinations AI SDXL Flux
**Resolution:** 1080x1080 (square, optimized for Instagram)
**No API key needed** for image generation

---

## Skill 6 — instagram-file-upload

**Triggers when:** User sends a photo or video file directly in Telegram (not a URL).

**Example user messages:**
- *(user attaches a photo and says)* "Post this to Instagram"
- *(user attaches a video)* "Share this as a Reel with casual tone"

**What it does:**
1. Reads the latest file from `~/.openclaw/media/inbound/`
2. Detects media type (IMAGE vs VIDEO) from file extension
3. Uploads file to imgbb (base64 encoded)
4. Generates caption via Multi-AI Router
5. Saves as PENDING draft
6. Shows preview and waits for YES or NO

**Supported file types:** .jpg, .jpeg, .png, .mp4, .mov
**Known limitation:** Vision model for image analysis sometimes times out. Bot still posts successfully with a generated caption based on any description the user provides in their message.

---

## Skill 7 — db-manager

**Triggers when:** User asks about storage, history, drafts, or database management.

**Example user messages:**
- "How much storage am I using?"
- "Show my recent posts"
- "List my pending drafts"
- "/storage"
- "/history"
- "Delete draft 5"

**What it does:**
- `storage` — shows DB file size and row counts per table
- `history` — shows last 10 posts with captions and post IDs
- `drafts` — shows all PENDING drafts
- `delete ID` — deletes a specific draft or history entry
- `clear_drafts` — deletes all pending drafts
- `clear_history` — clears all post history
- `ai_stats` — shows AI provider call counts and success rates

---

## Adding a Custom Skill

To add a new skill:

1. Create the skill folder:
```bash
mkdir -p ~/.openclaw/workspace/skills/my-skill
```

2. Create the SKILL.md:
```bash
cat > ~/.openclaw/workspace/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: What this skill does. Use when user asks about X or Y.
---
# My Skill

When user wants to do X, run:
~/my-script.sh ARGUMENT

Show the result to the user.
EOF
```

3. Create the shell script in the repo and home:
```bash
cat > ~/uct-insta-agent/my-script.sh << 'EOF'
#!/bin/bash
cd /teamspace/studios/this_studio/uct-insta-agent
/home/zeus/miniconda3/envs/cloudspace/bin/python3 pipelines/my_pipeline.py "$1"
EOF
chmod +x ~/uct-insta-agent/my-script.sh
cp ~/uct-insta-agent/my-script.sh ~/
```

4. Restart the gateway:
```bash
openclaw gateway run
```

---

*Built by Uniconverge Technologies Pvt. Ltd.*
