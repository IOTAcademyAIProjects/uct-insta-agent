# OpenClaw Skills Reference — ClawAgent v3.0

This repository provides 7 native OpenClaw skills that map Telegram user intents to specialized Python pipelines and CLI actions.

---

## 1. `instagram-post`
- **Description:** Post a single photo or video to Instagram with AI-generated, brand-aware captions.
- **Trigger:** When user sends an image URL and asks to post it to Instagram.
- **Command:** `~/post-to-instagram.sh "IMAGE_URL" "TONE" "DESCRIPTION"`

---

## 2. `instagram-carousel`
- **Description:** Post multiple images (2–10) as a single swipeable Instagram carousel.
- **Trigger:** When user provides 2 to 10 image URLs and asks for an album or carousel.
- **Command:** `~/post-carousel.sh "URL1,URL2,URL3" "TONE"`

---

## 3. `instagram-drafts` (Human-in-the-Loop)
- **Description:** Staged post creation with approval workflow.
- **Create:** `~/post-preview.sh "IMAGE_URL" "TONE" "DESCRIPTION"`
- **Approve:** `~/post-approve.sh DRAFT_ID`
- **Reject:** `~/post-reject.sh DRAFT_ID`
- **Update Caption:** `python3 cli.py update DRAFT_ID "NEW_CAPTION"`

---

## 4. `instagram-generate`
- **Description:** Generate an AI visual from a text prompt via Pollinations AI (Flux) and create a preview draft.
- **Trigger:** "Generate an image of...", "Create an AI visual of..."
- **Command:** `~/generate-image.sh "PROMPT" "TONE"`

---

## 5. `instagram-analytics`
- **Description:** Performance reporting with date filtering, content-type ranking, and strategic AI recommendations.
- **Trigger:** "Show my analytics", "How are my posts doing?", "/analytics"
- **Command:** `~/post-analytics.sh "DAYS"` (Default: 7 days)

---

## 6. `instagram-dm`
- **Description:** Direct message inbox and comment management.
- **Trigger:** "Check my DMs", "Show comments on post 123", "/dms"
- **Commands:**
  - Read DMs: `~/dm-manager.sh dms`
  - Read Comments: `~/dm-manager.sh comments POST_ID`
  - Delete Comment: `~/dm-manager.sh delete COMMENT_ID`

---

## 7. `instagram-scheduler`
- **Description:** Post immediate Instagram Stories or schedule future feed/story posts.
- **Trigger:** "Post to my story", "Schedule this for tomorrow at 5 PM"
- **Commands:**
  - Story: `~/post-story.sh "IMAGE_URL"`
  - Schedule: `~/scheduler.sh schedule "IMAGE_URL" "YYYY-MM-DD HH:MM"`
