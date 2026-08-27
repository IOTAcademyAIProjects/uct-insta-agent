#!/usr/bin/env python3
"""
AI Router — Backward-Compatible Wrapper for ClawAgent v3.0 Architecture
Routes requests through the core.model_router and db.repository modules.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from core.model_router import get_default_router
from db.repository import (
    log_ai_call, log_post, save_draft, delete_draft,
    get_storage_stats, get_post_history, get_pending_drafts
)

_router = get_default_router()

def generate_text(prompt, system_prompt=None, max_tokens=400):
    """Generate text using creative_writing task fallback chain."""
    return _router.generate_text("creative_writing", prompt, system_prompt=system_prompt, max_tokens=max_tokens)

def generate_caption(description, tone='casual', media_type='IMAGE'):
    """Generate social media caption with brand voice context."""
    system_prompt = (
        f"You are an expert social media manager and copywriter. "
        f"Write engaging, authentic Instagram captions with relevant hashtags in a {tone} tone. "
        f"Do not use quotes around the caption. Include 3-5 relevant hashtags at the end."
    )
    prompt = (
        f"Write a {tone} Instagram caption for a {media_type.lower()} post with the following details:\n\n"
        f"{description}\n\n"
        f"Requirements:\n"
        f"- Tone: {tone}\n"
        f"- Media type: {media_type}\n"
        f"- Length: 2-4 engaging sentences\n"
        f"- Include a subtle call to action\n"
        f"- End with 3-5 relevant hashtags\n"
        f"- No quotes around the response"
    )
    return _router.generate_text("creative_writing", prompt, system_prompt=system_prompt, max_tokens=300)

def generate_carousel_caption(image_count, tone='casual'):
    """Generate caption for carousel post."""
    system_prompt = (
        f"You are an expert social media manager. "
        f"Write engaging Instagram captions for multi-image swipeable carousel posts in a {tone} tone. "
        f"Do not use quotes. Include 3-5 relevant hashtags."
    )
    prompt = (
        f"Write a {tone} Instagram caption for a {image_count}-slide carousel post.\n\n"
        f"Requirements:\n"
        f"- Tone: {tone}\n"
        f"- Hook in the first line to encourage swiping\n"
        f"- Reference that this is a swipeable series ({image_count} slides)\n"
        f"- 2-4 sentences total\n"
        f"- Include a call-to-action (e.g., 'Swipe to see all ->', 'Save this for later')\n"
        f"- End with 3-5 relevant hashtags\n"
        f"- No quotes around the response"
    )
    return _router.generate_text("creative_writing", prompt, system_prompt=system_prompt, max_tokens=350)

def generate_analytics_summary(data_text, ranking_text, date_range):
    """Generate analytics summary using reasoning task chain."""
    system_prompt = (
        "You are an expert Instagram growth and analytics consultant. "
        "Summarize performance data into clear, actionable bullet points. "
        "Be concise, insightful, and focus on what the user should do next."
    )
    prompt = (
        f"Analyze this Instagram performance data for the period: {date_range}\n\n"
        f"POST PERFORMANCE DATA:\n{data_text}\n\n"
        f"CONTENT TYPE RANKING:\n{ranking_text}\n\n"
        f"Provide a summary with:\n"
        f"1. Best performing post and why it worked\n"
        f"2. Key performance trends\n"
        f"3. Which content type is driving the most engagement\n"
        f"4. One concrete recommendation for the next post\n\n"
        f"Keep it concise and formatted for easy reading in Telegram."
    )
    return _router.generate_text("reasoning", prompt, system_prompt=system_prompt, max_tokens=400)

def describe_image(image_url, prompt=None):
    """Describe image using vision task chain."""
    return _router.describe_image(image_url, prompt=prompt)

def get_router_status():
    """Return model router status dictionary."""
    return _router.get_status()

if __name__ == '__main__':
    print("AI Router v3.0 Status:")
    for prov, stat in _router.get_status().items():
        print(f"  {prov}: enabled={stat['enabled']}, creds={stat['has_credentials']}, state={stat['circuit_state']}")