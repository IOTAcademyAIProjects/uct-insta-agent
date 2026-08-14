#!/bin/bash
set -e
echo "Setting up uct-insta-agent..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install OpenClaw
npm install -g openclaw

# Install Node dependencies
npm install

# Install Python dependencies (free-tier only — no anthropic/paid deps required)
pip install composio-core python-dotenv requests openai --break-system-packages

# Make all repo shell scripts executable
chmod +x "$SCRIPT_DIR"/*.sh

echo ""
echo "Wiring up OpenClaw skills..."

# Copy the thin wrapper shell scripts to home directory (this is where
# OpenClaw's real skills expect to find them — see instructions below)
for script in dm-manager.sh generate-image.sh post-analytics.sh \
              post-approve.sh post-carousel.sh post-preview.sh \
              post-reject.sh post-story.sh post-to-instagram.sh scheduler.sh; do
  cp "$SCRIPT_DIR/$script" ~/"$script"
  chmod +x ~/"$script"
done

# Create the 7 real OpenClaw skills (native SKILL.md format at
# ~/.openclaw/workspace/skills/ — this is a SEPARATE system from
# anything in this repo's own skills/ folder, if one exists)
mkdir -p ~/.openclaw/workspace/skills/instagram-post
cat > ~/.openclaw/workspace/skills/instagram-post/skill.js << 'JSEOF'
const { execFile } = require('child_process');
const path = require('path');
const { promisify } = require('util');

const execFileAsync = promisify(execFile);
const PROJECT_DIR = process.env.UCT_INSTA_AGENT_DIR || require('os').homedir() + '/uct-insta-agent';

module.exports = {
  name: 'instagram_post',
  description: 'Post an image to Instagram with an AI-generated caption. Use when user wants to post an image to Instagram. Can accept an image URL and optional description or tone.',

  inputSchema: {
    type: 'object',
    properties: {
      image_url: { type: 'string', description: 'The URL of the image to post to Instagram' },
      description: { type: 'string', description: 'Description of the image for caption generation. If omitted, the image is described automatically via vision.' },
      tone: { type: 'string', description: 'Tone: inspirational, casual, professional, funny' }
    },
    required: ['image_url']
  },

  async run({ image_url, description, tone = 'casual' }) {
    try {
      const scriptPath = path.join(PROJECT_DIR, 'pipelines', 'post-with-caption.py');
      const args = [scriptPath, image_url, tone];
      if (description) args.push(description);

      const { stdout } = await execFileAsync('python3', args, {
        cwd: PROJECT_DIR,
        env: { ...process.env },
        timeout: 60000
      });

      const result = stdout.trim();
      if (result.includes('SUCCESS')) {
        const postId = result.match(/Post ID: (.+)/)?.[1] || 'unknown';
        return `✅ Posted to Instagram!\nPost ID: ${postId}\nCheck: https://instagram.com/YOUR_USERNAME`;
      }
      return `❌ Failed: ${result}`;
    } catch (error) {
      const detail = error.stderr || error.stdout || error.message;
      return `❌ Error: ${detail}`;
    }
  }
};
JSEOF

mkdir -p ~/.openclaw/workspace/skills/instagram-analytics
cat > ~/.openclaw/workspace/skills/instagram-analytics/SKILL.md << 'MDEOF'
---
name: instagram-analytics
description: Get Instagram performance analytics, engagement stats, and content recommendations. Use when user asks about analytics, performance, stats, how posts are doing, or which type of content works best.
---
# Instagram Analytics

When user wants Instagram performance data, run this command:

```bash
~/post-analytics.sh "ARG1" "ARG2"
```

## Argument patterns
- No date mentioned (default last 7 days): `~/post-analytics.sh`
- User says "last N days" or "last month": `~/post-analytics.sh "N"`
- User gives a specific date range "from X to Y": `~/post-analytics.sh "YYYY-MM-DD" "YYYY-MM-DD"`

## What the report includes
- Best performing individual post
- Total reach and engagement for the period
- Which content type (image/video/carousel) gets the best engagement
- One actionable recommendation
MDEOF

mkdir -p ~/.openclaw/workspace/skills/instagram-carousel
cat > ~/.openclaw/workspace/skills/instagram-carousel/SKILL.md << 'MDEOF'
---
name: instagram-carousel
description: Post multiple images (2-10) to Instagram as a single swipeable carousel. Use when user wants to post a carousel, album, or multiple images together to Instagram.
---
# Instagram Carousel Post

When user wants to post a carousel (2-10 images) to Instagram, run this command:

```bash
~/post-carousel.sh "URL1,URL2,URL3" "TONE"
```

Image URLs must be comma-separated with no spaces. Minimum 2, maximum 10 images.
Default tone: casual. One unified caption is generated for the whole carousel.
MDEOF

mkdir -p ~/.openclaw/workspace/skills/instagram-dm
cat > ~/.openclaw/workspace/skills/instagram-dm/SKILL.md << 'MDEOF'
---
name: instagram-dm
description: Manage Instagram DMs and comments. Read DM inbox, view comments on posts, delete comments, get activity summary. Use when user asks about DMs, messages, comments, or engagement.
---
# Instagram DMs & Comments

## Read DM inbox
User says: "show my DMs", "check messages", "/dms"
Run: `~/dm-manager.sh dms`

## Read comments
User says: "show comments on post 123"
Run: `~/dm-manager.sh comments POST_ID`

## Delete a comment
User says: "delete comment 789"
Run: `~/dm-manager.sh delete COMMENT_ID`

## Activity summary
User says: "how is my engagement?"
Run: `~/dm-manager.sh summary`
MDEOF

mkdir -p ~/.openclaw/workspace/skills/instagram-file-upload
cat > ~/.openclaw/workspace/skills/instagram-file-upload/SKILL.md << 'MDEOF'
---
name: instagram-file-upload
description: Handle image or video files sent directly via Telegram as attachments. Use when user sends a photo or file directly in chat. ALWAYS show preview first and wait for approval before posting.
---
# Instagram File Upload — Preview Required

CRITICAL RULE: NEVER post directly. ALWAYS show preview and wait for YES.

## Step 1 - Run the file handler
```bash
cd ~/uct-insta-agent && python3 pipelines/file_upload_handler.py "$(ls -t ~/.openclaw/media/inbound/ | head -1)" "TONE"
```

## Step 2 - STOP. Send preview and WAIT
After running the script, show the CAPTION from script output and ask:
"Reply: YES — post to Instagram | NO — cancel"
Then STOP and wait for user reply. Do not post automatically.

## Step 3 - Only after user replies YES
```bash
~/post-approve.sh DRAFT_ID
```

## Step 4 - If user replies NO
```bash
~/post-reject.sh DRAFT_ID
```
MDEOF

mkdir -p ~/.openclaw/workspace/skills/instagram-generate
cat > ~/.openclaw/workspace/skills/instagram-generate/SKILL.md << 'MDEOF'
---
name: instagram-generate
description: Generate an AI image from a text description and post it to Instagram. Use when user wants to generate or create an AI image, artwork, or visual using artificial intelligence.
---
# AI Image Generation

When user wants to generate an AI image, run:

```bash
~/generate-image.sh "IMAGE_DESCRIPTION" "TONE"
```

Then show the preview and ask YES/NO before posting.
If YES: run `~/post-approve.sh DRAFT_ID`
If NO: run `~/post-reject.sh DRAFT_ID`

Default tone: casual
MDEOF

mkdir -p ~/.openclaw/workspace/skills/instagram-drafts
cat > ~/.openclaw/workspace/skills/instagram-drafts/SKILL.md << 'MDEOF'
---
name: instagram-drafts
description: Create a draft Instagram post from an image URL, then approve, reject, or update it before publishing. Use when user wants to create a draft, preview a post before it goes live, or asks to post from a URL (not a directly-attached file — that's instagram-file-upload).
---
# Instagram Drafts — create / approve / reject / update

## Create a draft from an image URL
Run:
```bash
~/post-preview.sh "IMAGE_URL" "TONE" "DESCRIPTION"
```
DESCRIPTION is optional — if omitted, the image is described automatically via vision.

After running, show the caption and image, then ALWAYS wait:
"Reply: approve [id] | reject [id] | update [id] [new caption]"
Do NOT post automatically.

## Approve
Run: `~/post-approve.sh DRAFT_ID`

## Reject
Run: `~/post-reject.sh DRAFT_ID`

## Update
Run: `cd ~/uct-insta-agent && python3 pipelines/preview.py update DRAFT_ID "NEW_CAPTION"`
MDEOF

echo ""
echo "Setting up database..."
python3 db/setup_db.py

echo ""
echo "Done! Now:"
echo "1. Fill in your .env file (see .env.example)"
echo "2. Run: openclaw models auth login --provider openrouter --method api-key"
echo "   (needed for free vision-based captions)"
echo "3. Run: openclaw config set agents.defaults.imageModel.primary \"openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free\""
echo "4. Run: openclaw gateway run"