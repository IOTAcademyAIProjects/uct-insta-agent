# uct-insta-agent — Self Help Guide

Everything you need to manage, troubleshoot, and extend the bot yourself.

---

## Table of Contents

1. [Session Restore (Lightning.ai)](#1-session-restore-lightningai)
2. [Switching AI Models](#2-switching-ai-models)
3. [Adding a New AI Provider](#3-adding-a-new-ai-provider)
4. [Rate Limit Troubleshooting](#4-rate-limit-troubleshooting)
5. [Check Which Model is Active](#5-check-which-model-is-active)
6. [Database Management](#6-database-management)
7. [Shell Script Reference](#7-shell-script-reference)
8. [OpenClaw Skills Management](#8-openclaw-skills-management)
9. [Common Errors and Fixes](#9-common-errors-and-fixes)
10. [API Keys Reference](#10-api-keys-reference)

---

## 1. Session Restore (Lightning.ai)

Every new Lightning.ai session needs this setup. Run in order:

```bash
# Step 1 — go to project
cd ~/uct-insta-agent

# Step 2 — upgrade Node if needed (OpenClaw needs v24+)
nvm install 24
nvm use 24

# Step 3 — install OpenClaw
npm install -g openclaw

# Step 4 — install Python packages
pip install openai requests python-dotenv composio-core Pillow --break-system-packages

# Step 5 — copy shell scripts to home
for f in *.sh; do cp "$f" ~/ && chmod +x ~/"$f"; done

# Step 6 — initialize database
python3 db/setup_db.py

# Step 7 — switch OpenClaw brain to NVIDIA (see Section 2)
# Step 8 — recreate OpenClaw skills (see Section 8)
# Step 9 — start the gateway
openclaw gateway run
```

---

## 2. Switching AI Models

### Switch OpenClaw brain to NVIDIA NIM (recommended)

```bash
NVIDIA_KEY=$(grep NVIDIA_API_KEY .env | cut -d'=' -f2)

python3 -c "
import json
config_path = '/teamspace/studios/this_studio/.openclaw/openclaw.json'
with open(config_path) as f:
    config = json.load(f)
config['models'] = {'providers': {'nvidia': {
    'baseUrl': 'https://integrate.api.nvidia.com/v1',
    'apiKey': '$NVIDIA_KEY',
    'api': 'openai-completions',
    'models': [{'id': 'z-ai/glm-5.2', 'name': 'GLM 5.2', 'contextWindow': 195000, 'maxTokens': 8192, 'input': ['text']}]
}}}
config['agents']['defaults']['models'] = {'nvidia/z-ai/glm-5.2': {}}
config['agents']['defaults']['model'] = {'primary': 'nvidia/z-ai/glm-5.2'}
config['plugins']['entries']['anthropic'] = {'enabled': False}
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)
print('Switched to NVIDIA NIM!')
"
```

### Switch OpenClaw brain to Cerebras

```bash
CEREBRAS_KEY=$(grep CEREBRAS_API_KEY .env | cut -d'=' -f2)

python3 -c "
import json
config_path = '/teamspace/studios/this_studio/.openclaw/openclaw.json'
with open(config_path) as f:
    config = json.load(f)
config['models']['providers']['cerebras'] = {
    'baseUrl': 'https://api.cerebras.ai/v1',
    'apiKey': '$CEREBRAS_KEY',
    'api': 'openai-completions',
    'models': [{'id': 'gpt-oss-120b', 'name': 'Cerebras GPT', 'contextWindow': 128000, 'maxTokens': 8192, 'input': ['text']}]
}
config['agents']['defaults']['models'] = {'cerebras/gpt-oss-120b': {}}
config['agents']['defaults']['model'] = {'primary': 'cerebras/gpt-oss-120b'}
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)
print('Switched to Cerebras!')
"
```

### Switch OpenClaw brain to Mistral

```bash
MISTRAL_KEY=$(grep MISTRAL_API_KEY .env | cut -d'=' -f2)

python3 -c "
import json
config_path = '/teamspace/studios/this_studio/.openclaw/openclaw.json'
with open(config_path) as f:
    config = json.load(f)
config['models']['providers']['mistral'] = {
    'baseUrl': 'https://api.mistral.ai/v1',
    'apiKey': '$MISTRAL_KEY',
    'api': 'openai-completions',
    'models': [{'id': 'mistral-large-latest', 'name': 'Mistral Large', 'contextWindow': 128000, 'maxTokens': 8192, 'input': ['text']}]
}
config['agents']['defaults']['models'] = {'mistral/mistral-large-latest': {}}
config['agents']['defaults']['model'] = {'primary': 'mistral/mistral-large-latest'}
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)
print('Switched to Mistral!')
"
```

### Switch caption generation model (AI Router)

Edit `pipelines/ai_router.py` and update the PROVIDERS list:

```python
PROVIDERS = [
    {
        "name": "NVIDIA",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "model": "z-ai/glm-5.2",       # change model name here
    },
    {
        "name": "CEREBRAS",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "model": "gpt-oss-120b",        # change model name here
    },
    {
        "name": "MISTRAL",
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "model": "mistral-large-latest", # change model name here
    },
]
```

Available NVIDIA models: check build.nvidia.com/models (free endpoint only)
Available Cerebras models: run `python3 -c "from openai import OpenAI; import os; from dotenv import load_dotenv; load_dotenv(); c=OpenAI(base_url='https://api.cerebras.ai/v1',api_key=os.getenv('CEREBRAS_API_KEY')); [print(m.id) for m in c.models.list()]"`
Available Mistral models: mistral-large-latest, mistral-medium-latest, open-mistral-7b

---

## 3. Adding a New AI Provider

Any OpenAI-compatible API can be added to the router. Edit `pipelines/ai_router.py`:

```python
# Add to PROVIDERS list
{
    "name": "YOUR_PROVIDER",
    "base_url": "https://api.yourprovider.com/v1",
    "api_key_env": "YOUR_PROVIDER_API_KEY",
    "model": "model-name-here",
},
```

Then add the key to `.env`:
```
YOUR_PROVIDER_API_KEY=your_key_here
```

### Free providers that work in India (no credit card)

| Provider | Sign Up | Base URL | Good Models |
|---|---|---|---|
| NVIDIA NIM | build.nvidia.com | https://integrate.api.nvidia.com/v1 | z-ai/glm-5.2 |
| Cerebras | inference.cerebras.ai | https://api.cerebras.ai/v1 | gpt-oss-120b |
| Mistral | console.mistral.ai | https://api.mistral.ai/v1 | mistral-large-latest |
| OpenRouter | openrouter.ai | https://openrouter.ai/api/v1 | many free models |
| Together AI | api.together.ai | https://api.together.xyz/v1 | Llama 3.1 70B |

### Adding OpenRouter (recommended 4th provider)

```bash
# Add to .env
echo "OPENROUTER_API_KEY=sk-or-xxxxxx" >> .env

# Add to ai_router.py PROVIDERS list:
# {
#     "name": "OPENROUTER",
#     "base_url": "https://openrouter.ai/api/v1",
#     "api_key_env": "OPENROUTER_API_KEY",
#     "model": "meta-llama/llama-3.1-8b-instruct:free",
# },
```

---

## 4. Rate Limit Troubleshooting

### Symptoms
- Bot replies: "All models are temporarily rate-limited"
- Gateway log shows: `status=429`
- Error: `API rate limit reached. Please try again later`

### Quick fix — switch active OpenClaw brain
```bash
# If NVIDIA is rate limited, switch to Cerebras:
# (run the Cerebras switch command from Section 2)
# Then restart: openclaw gateway run

# If Cerebras is rate limited, switch to Mistral:
# (run the Mistral switch command from Section 2)
# Then restart: openclaw gateway run
```

### Check current rotation position
```bash
cat db/ai_rotation.json
```

### Reset rotation to provider 0 (NVIDIA)
```bash
python3 -c "
import json
with open('db/ai_rotation.json', 'w') as f:
    json.dump({'index': 0, 'last_updated': 'reset'}, f)
print('Reset to provider 0 (NVIDIA)')
"
```

### Rate limit reset times
| Provider | Reset Period |
|---|---|
| NVIDIA NIM | Per minute (40 RPM) + daily credits |
| Cerebras | Per minute + daily (1M tokens/day) |
| Mistral | Per minute + monthly (~1B tokens) |

### Prevention
The AI Router automatically rotates providers to spread load. Rate limits only occur when many requests are made in rapid succession (e.g. testing everything at once). In normal daily use (a few posts per day) limits are never hit.

---

## 5. Check Which Model is Active

### Check OpenClaw brain
```bash
python3 -c "
import json
with open('/teamspace/studios/this_studio/.openclaw/openclaw.json') as f:
    config = json.load(f)
print('Primary model:', config['agents']['defaults']['model']['primary'])
print('Available:', list(config['agents']['defaults']['models'].keys()))
"
```

### Check AI Router current provider
```bash
python3 -c "
import sys
sys.path.insert(0, '/teamspace/studios/this_studio/uct-insta-agent')
from pipelines.ai_router import get_router_status
status = get_router_status()
print('Current provider:', status['current_provider'])
print('Current model:', status['current_model'])
print('All providers:', status['providers'])
"
```

### Check from gateway log
```bash
tail -5 /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log | grep model
```

### Test all providers
```bash
python3 pipelines/ai_router.py
```

---

## 6. Database Management

### Check storage stats
```bash
python3 pipelines/db_manager.py storage
```

### View post history
```bash
python3 pipelines/db_manager.py history
# or last N posts:
python3 pipelines/db_manager.py history 20
```

### View pending drafts
```bash
python3 pipelines/db_manager.py drafts
```

### Delete a draft
```bash
python3 pipelines/db_manager.py delete DRAFT_ID
```

### Clear all pending drafts
```bash
python3 pipelines/db_manager.py clear_drafts
```

### Clear post history
```bash
python3 pipelines/db_manager.py clear_history
```

### View AI call stats
```bash
python3 pipelines/db_manager.py ai_stats
```

### View scheduled posts
```bash
~/scheduler.sh list
```

### Cancel a scheduled post
```bash
~/scheduler.sh cancel POST_ID
```

### Run scheduler manually (publish due posts)
```bash
~/scheduler.sh run
```

### Direct SQLite access
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('db/uct_agent.sqlite')
# List all tables
tables = conn.execute('SELECT name FROM sqlite_master WHERE type=table').fetchall()
print('Tables:', [t[0] for t in tables])
conn.close()
"
```

---

## 7. Shell Script Reference

All scripts live in both the repo root and `~/` (home directory).

| Script | What it does | Example |
|---|---|---|
| `post-to-instagram.sh` | Post image/video via URL | `~/post-to-instagram.sh "https://..." "description" "casual"` |
| `post-carousel.sh` | Post 2-10 images as carousel | `~/post-carousel.sh "url1,url2,url3" "inspirational"` |
| `post-preview.sh` | Create draft with preview | `~/post-preview.sh "https://..." "casual"` |
| `post-approve.sh` | Approve and publish a draft | `~/post-approve.sh 15` |
| `post-reject.sh` | Cancel a draft | `~/post-reject.sh 15` |
| `post-story.sh` | Post Instagram Story | `~/post-story.sh "https://..."` |
| `post-analytics.sh` | Run analytics report | `~/post-analytics.sh` or `~/post-analytics.sh 30` |
| `generate-image.sh` | Generate AI image | `~/generate-image.sh "futuristic city at night" "inspirational"` |
| `dm-manager.sh` | Manage DMs and comments | `~/dm-manager.sh dms` |
| `scheduler.sh` | Schedule future posts | `~/scheduler.sh schedule "url" "2026-09-01 09:00" "casual"` |

### Recreate all shell scripts (if lost after session reset)
```bash
cd ~/uct-insta-agent
for f in *.sh; do cp "$f" ~/ && chmod +x ~/"$f"; done
echo "All shell scripts restored!"
```

---

## 8. OpenClaw Skills Management

Skills tell the OpenClaw bot what to do. They live in `~/.openclaw/workspace/skills/` and must be recreated on every new Lightning.ai session.

### Check which skills exist
```bash
ls ~/.openclaw/workspace/skills/
```

### Read a skill
```bash
cat ~/.openclaw/workspace/skills/instagram-post/SKILL.md
```

### Recreate all skills (run after each new session)
```bash
python3 -c "
import os

base = '/teamspace/studios/this_studio/.openclaw/workspace/skills'
skills = {
    'instagram-post': '''---
name: instagram-post
description: Post images or videos to Instagram with AI captions. Use when user wants to post to Instagram via URL.
---
When user wants to post to Instagram run:
~/post-preview.sh IMAGE_URL TONE
Show DRAFT_ID and CAPTION to user. Wait for YES or NO.
IMPORTANT: When user replies YES — immediately run: ~/post-approve.sh DRAFT_ID
When user replies NO — immediately run: ~/post-reject.sh DRAFT_ID
Default TONE: casual''',

    'instagram-carousel': '''---
name: instagram-carousel
description: Post multiple images as Instagram carousel. Use when user wants carousel or multiple images.
---
Run: ~/post-carousel.sh URL1,URL2,URL3 TONE
Minimum 2 images, maximum 10. Comma separated, no spaces.
Show result to user.''',

    'instagram-analytics': '''---
name: instagram-analytics
description: Get Instagram analytics and performance stats. Use when user asks about analytics, performance, stats, engagement.
---
Default 7 days: ~/post-analytics.sh
Custom days: ~/post-analytics.sh 30
Custom range: ~/post-analytics.sh 2026-06-01 2026-06-30''',

    'instagram-dm': '''---
name: instagram-dm
description: Manage Instagram DMs and comments. Use when user asks about DMs, messages, comments, engagement.
---
Show DMs: ~/dm-manager.sh dms
Notify new DMs: ~/dm-manager.sh notify
Show comments: ~/dm-manager.sh comments POST_ID
Delete comment: ~/dm-manager.sh delete COMMENT_ID
Summary: ~/dm-manager.sh summary''',

    'instagram-generate': '''---
name: instagram-generate
description: Generate AI image from text description and post to Instagram. Use when user wants to generate or create an AI image.
---
Run: ~/generate-image.sh DESCRIPTION TONE
Shows DRAFT_ID and CAPTION. Wait for YES or NO.
If YES: ~/post-approve.sh DRAFT_ID
If NO: ~/post-reject.sh DRAFT_ID''',

    'instagram-file-upload': '''---
name: instagram-file-upload
description: Handle photo or video files sent directly in Telegram chat. Use when user sends a photo or video file attachment directly.
---
IMPORTANT: Never post without YES from user.
Step 1 - Run file handler:
LATEST=$(ls -t /teamspace/studios/this_studio/.openclaw/media/inbound/*.jpg /teamspace/studios/this_studio/.openclaw/media/inbound/*.mp4 2>/dev/null | head -1) && cd /teamspace/studios/this_studio/uct-insta-agent && /home/zeus/miniconda3/envs/cloudspace/bin/python3 pipelines/file_upload_handler.py \"$LATEST\" casual
Step 2 - Show DRAFT_ID and CAPTION to user and say: Reply YES to post or NO to cancel
If YES: ~/post-approve.sh DRAFT_ID
If NO: ~/post-reject.sh DRAFT_ID''',

    'db-manager': '''---
name: db-manager
description: Manage local database. Use when user asks about storage, history, drafts, database, scheduled posts.
---
Storage stats: python3 /teamspace/studios/this_studio/uct-insta-agent/pipelines/db_manager.py storage
Post history: python3 /teamspace/studios/this_studio/uct-insta-agent/pipelines/db_manager.py history
Pending drafts: python3 /teamspace/studios/this_studio/uct-insta-agent/pipelines/db_manager.py drafts
Delete entry: python3 /teamspace/studios/this_studio/uct-insta-agent/pipelines/db_manager.py delete ID
Clear drafts: python3 /teamspace/studios/this_studio/uct-insta-agent/pipelines/db_manager.py clear_drafts
AI stats: python3 /teamspace/studios/this_studio/uct-insta-agent/pipelines/db_manager.py ai_stats'''
}

for name, content in skills.items():
    os.makedirs(f'{base}/{name}', exist_ok=True)
    with open(f'{base}/{name}/SKILL.md', 'w') as f:
        f.write(content)
    print(f'Skill created: {name}')

print('All skills recreated!')
"
```

---

## 9. Common Errors and Fixes

### openclaw: command not found
```bash
nvm use 24
npm install -g openclaw
```

### Gateway failed to start: Invalid config
```bash
# Restore from backup
cp ~/.openclaw/openclaw.json.bak ~/.openclaw/openclaw.json
openclaw gateway run
```

### API rate limit reached (429)
Switch to a different provider — see Section 2 and Section 4.

### Draft not found or already processed
The draft was already approved, rejected, or expired. Create a new one:
```bash
~/post-preview.sh "IMAGE_URL" "tone"
```

### Composio connection error
```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
from composio import Composio
client = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
accounts = client.connected_accounts.list()
items = dict(accounts)['items']
print('Status:', items[0].status)
"
```
If it shows error, go to composio.dev and reconnect your Instagram account.

### Bot not responding in Telegram
1. Check gateway is running: `openclaw gateway run`
2. Check your Telegram ID is in allowlist:
```bash
cat ~/.openclaw/credentials/telegram-default-allowFrom.json
```
3. Re-pair if needed: message the bot, get pairing code, run:
```bash
openclaw pairing approve telegram YOUR_CODE
```

### setup.sh fails with heredoc error
Run setup manually:
```bash
npm install -g openclaw
npm install
pip install openai requests python-dotenv composio-core --break-system-packages
python3 db/setup_db.py
for f in *.sh; do cp "$f" ~/ && chmod +x ~/"$f"; done
```

### Vision model timing out
This is a known issue. The bot still posts but uses a generic caption.
Workaround: add a description in your Telegram message.
Example: "Post this sunset photo to Instagram" — the bot uses "sunset photo" as the description.

---

## 10. API Keys Reference

All keys go in `.env` file in the project root. Never commit this file.

| Variable | Source | Notes |
|---|---|---|
| TELEGRAM_BOT_TOKEN | @BotFather → /mybots → @uct_clawgram_bot → API Token | Rotate before M11 public release |
| COMPOSIO_API_KEY | composio.dev → aiprojects project → Settings → API Keys | Project-specific key |
| COMPOSIO_ACCOUNT_ID | Fixed: ac_A7GnunIEtMTb | Instagram auth config |
| INSTAGRAM_USER_ID | Fixed: 26796203086728345 | @iot_academy_projects numeric ID |
| IMGBB_API_KEY | api.imgbb.com (free, just sign in) | For public image hosting |
| NVIDIA_API_KEY | build.nvidia.com → free endpoint → API Keys | Starts with nvapi- |
| CEREBRAS_API_KEY | inference.cerebras.ai → free signup | Starts with csk- |
| MISTRAL_API_KEY | console.mistral.ai → free signup | Random characters |
| GPU_ENABLED | Set to false for CPU studio | Set to true only for M8/M9 GPU work |
| POST_TIMEZONE | Asia/Kolkata | Affects scheduled post times |
| DB_PATH | db/uct_agent.sqlite | Local SQLite database path |

### Check which keys are set
```bash
grep -v "^#" .env | grep "=" | sed 's/=.*/=***/'
```

### Test all API connections
```bash
python3 pipelines/ai_router.py
```

---

## Quick Reference Card

```
Start bot:          openclaw gateway run
Stop bot:           Ctrl+C
Switch to NVIDIA:   See Section 2
Switch to Mistral:  See Section 2
Rate limited:       See Section 4
Post image:         ~/post-preview.sh "URL" "tone"
Approve post:       ~/post-approve.sh DRAFT_ID
Check storage:      python3 pipelines/db_manager.py storage
Check history:      python3 pipelines/db_manager.py history
Test AI Router:     python3 pipelines/ai_router.py
Recreate skills:    See Section 8
Full session setup: See Section 1
```

---

*Built by Uniconverge Technologies Pvt. Ltd. — www.uniconvergetech.in*
*© 2026 All Rights Reserved*
