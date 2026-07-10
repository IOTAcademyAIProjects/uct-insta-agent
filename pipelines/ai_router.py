#!/usr/bin/env python3
"""
Multi-AI Router — Round Robin + Fallback
Rotates across NVIDIA, Cerebras, and Mistral free providers.
Usage: from pipelines.ai_router import generate_text
"""

import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('/teamspace/studios/this_studio/uct-insta-agent/.env')

# ----------------------------------------------------------------
# PROVIDER CONFIG
# ----------------------------------------------------------------

PROVIDERS = [
    {
        "name": "NVIDIA",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "model": "z-ai/glm-5.2",
    },
    {
        "name": "CEREBRAS",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "model": "gpt-oss-120b",
    },
    {
        "name": "MISTRAL",
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "model": "mistral-large-latest",
    },
]

# Rotation state file
ROTATION_FILE = os.path.join(
    os.path.dirname(__file__), '..', 'db', 'ai_rotation.json'
)

# ----------------------------------------------------------------
# ROTATION STATE
# ----------------------------------------------------------------

def load_index():
    """Load current provider index from file"""
    try:
        os.makedirs(os.path.dirname(ROTATION_FILE), exist_ok=True)
        if os.path.exists(ROTATION_FILE):
            with open(ROTATION_FILE, 'r') as f:
                data = json.load(f)
                return data.get('index', 0)
    except Exception:
        pass
    return 0


def save_index(index):
    """Save current provider index to file"""
    try:
        os.makedirs(os.path.dirname(ROTATION_FILE), exist_ok=True)
        with open(ROTATION_FILE, 'w') as f:
            json.dump({
                'index': index,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f)
    except Exception:
        pass


# ----------------------------------------------------------------
# CORE GENERATE FUNCTION
# ----------------------------------------------------------------

def generate_text(prompt, system_prompt=None, max_tokens=400):
    """
    Generate text using Round Robin + Fallback across providers.
    Tries each provider in rotation order, falls back on failure.
    """
    current_index = load_index()
    total = len(PROVIDERS)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Try each provider starting from current index
    for attempt in range(total):
        provider_index = (current_index + attempt) % total
        provider = PROVIDERS[provider_index]

        api_key = os.getenv(provider['api_key_env'])
        if not api_key:
            print(f"[AI Router] {provider['name']}: No API key — skipping")
            continue

        try:
            print(f"[AI Router] Trying {provider['name']} ({provider['model']})...")

            client = OpenAI(
                base_url=provider['base_url'],
                api_key=api_key
            )

            response = client.chat.completions.create(
                model=provider['model'],
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.8
            )

            result = response.choices[0].message.content.strip()

            # Advance rotation to next provider for next call
            next_index = (provider_index + 1) % total
            save_index(next_index)

            print(f"[AI Router] SUCCESS — {provider['name']}")
            return result

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"[AI Router] {provider['name']} FAILED: {error_msg}")
            continue

    raise Exception("All AI providers failed — check API keys and rate limits")


# ----------------------------------------------------------------
# CAPTION GENERATION (replaces Claude caption function)
# ----------------------------------------------------------------

def generate_caption(description, tone='casual', media_type='IMAGE'):
    """Generate Instagram caption with hashtags"""
    prompt = f"""Generate an Instagram caption for this {media_type.lower()}: "{description}"
Tone: {tone}

Requirements:
1. 2-3 sentences, engaging and authentic
2. 5-7 relevant hashtags at the end
3. A call to action

Return only the caption and hashtags, nothing else."""

    return generate_text(prompt, max_tokens=300)


def generate_analytics_summary(data_text, ranking_text, date_range):
    """Generate analytics summary in plain English"""
    prompt = f"""Summarize Instagram performance for a Telegram message.
Date range: {date_range}

Post data:
{data_text}

Content type ranking:
{ranking_text}

Write a friendly plain-English summary covering:
1. Best performing post
2. Total reach and engagement
3. Which content type the audience prefers and a recommendation
4. One actionable tip

Keep it conversational, max 8 sentences."""

    return generate_text(prompt, max_tokens=500)


def generate_carousel_caption(image_count, tone='casual'):
    """Generate caption for carousel posts"""
    prompt = f"""Generate an Instagram caption for a carousel post with {image_count} images.
Tone: {tone}

Requirements:
1. 2-3 sentences mentioning it is a series
2. 5-7 hashtags
3. Call to action like swipe to see more

Return only caption and hashtags."""

    return generate_text(prompt, max_tokens=300)


# ----------------------------------------------------------------
# STATUS & TEST
# ----------------------------------------------------------------

def get_router_status():
    """Return current router status"""
    current_index = load_index()
    current = PROVIDERS[current_index % len(PROVIDERS)]
    return {
        'current_provider': current['name'],
        'current_model': current['model'],
        'total_providers': len(PROVIDERS),
        'providers': [p['name'] for p in PROVIDERS]
    }


if __name__ == '__main__':
    import sys

    if '--status' in sys.argv:
        status = get_router_status()
        print(f"Current provider: {status['current_provider']}")
        print(f"Current model: {status['current_model']}")
        print(f"All providers: {', '.join(status['providers'])}")

    else:
        print("Testing all providers...\n")
        test_prompt = "Generate a short Instagram caption for a mountain sunset. Add 3 hashtags."

        for i, provider in enumerate(PROVIDERS):
            api_key = os.getenv(provider['api_key_env'])
            if not api_key:
                print(f"{provider['name']}: SKIPPED — no key")
                continue
            try:
                client = OpenAI(base_url=provider['base_url'], api_key=api_key)
                response = client.chat.completions.create(
                    model=provider['model'],
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=100
                )
                print(f"{provider['name']}: OK")
                print(f"  {response.choices[0].message.content[:80]}")
            except Exception as e:
                print(f"{provider['name']}: FAILED — {str(e)[:60]}")
            print()


# ----------------------------------------------------------------
# DATABASE LOGGING
# ----------------------------------------------------------------

DB_PATH = '/teamspace/studios/this_studio/uct-insta-agent/db/uct_agent.sqlite'

def log_ai_call(provider, model, prompt_type, success):
    """Log every AI call to the database"""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            'INSERT INTO ai_calls (provider, model, prompt_type, success) VALUES (?, ?, ?, ?)',
            (provider, model, prompt_type, 1 if success else 0)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        pass  # Never block on logging failure


def log_post(post_id, caption, media_type, tone, image_url, provider):
    """Log every successful Instagram post to the database"""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            '''INSERT OR IGNORE INTO posts
               (post_id, caption, media_type, tone, image_url, provider)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (post_id, caption, media_type, tone, image_url, provider)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        pass


def save_draft(image_url, caption, tone, media_type):
    """Save a draft to the database — returns draft ID"""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute(
            '''INSERT INTO drafts (image_url, caption, tone, media_type, status)
               VALUES (?, ?, ?, ?, "PENDING")''',
            (image_url, caption, tone, media_type)
        )
        draft_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return draft_id
    except Exception as e:
        return None


def delete_draft(draft_id):
    """Delete a draft by ID"""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.execute('DELETE FROM drafts WHERE id = ?', (draft_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_storage_stats():
    """Return database storage statistics"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    stats = {}
    for table in ['posts', 'drafts', 'analytics_cache', 'ai_calls']:
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        stats[table] = count
    conn.close()

    # DB file size
    size_bytes = os.path.getsize(DB_PATH)
    size_kb = round(size_bytes / 1024, 2)

    return {
        'size_kb': size_kb,
        'posts': stats['posts'],
        'drafts': stats['drafts'],
        'analytics_cache': stats['analytics_cache'],
        'ai_calls': stats['ai_calls']
    }


def get_post_history(limit=10):
    """Return last N posts from history"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        '''SELECT id, post_id, caption, media_type, provider, timestamp
           FROM posts ORDER BY timestamp DESC LIMIT ?''',
        (limit,)
    ).fetchall()
    conn.close()
    return rows


def get_pending_drafts():
    """Return all pending drafts"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        '''SELECT id, image_url, caption, tone, media_type, created_at
           FROM drafts WHERE status = "PENDING"
           ORDER BY created_at DESC'''
    ).fetchall()
    conn.close()
    return rows
