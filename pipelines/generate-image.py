#!/usr/bin/env python3
"""
M8 — AI Image Generation Pipeline
Uses Pollinations AI (free, no API key) to generate images from text prompts.
Then uploads to imgbb and creates a draft for preview before posting.
Usage: python3 pipelines/generate-image.py "your image description" [tone]
"""

import os
import sys
import time
import requests
import sqlite3
from urllib.parse import quote
sys.path.insert(0, '/teamspace/studios/this_studio/uct-insta-agent')
from dotenv import load_dotenv
load_dotenv('/teamspace/studios/this_studio/uct-insta-agent/.env')
from pipelines.ai_router import generate_text

DB_PATH = '/teamspace/studios/this_studio/uct-insta-agent/db/uct_agent.sqlite'

#----------------------------------------------------------------
# IMAGE GENERATION — Pollinations AI
#----------------------------------------------------------------

def generate_image(prompt, width=1080, height=1080, model='flux'):
    """Generate image using Pollinations AI — free, no API key"""
    encoded_prompt = quote(prompt)
    seed = int(time.time()) % 9999

    # Primary: Pollinations with flux model
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model={model}&seed={seed}&nologo=true&enhance=true"

    print(f"Generating image with Pollinations AI...")
    print(f"Prompt: {prompt[:60]}...")

    response = requests.get(url, timeout=60)

    if response.status_code == 200 and len(response.content) > 5000:
        print(f"Image generated: {len(response.content)/1024:.1f} KB")
        return response.content

    # Fallback: try turbo model
    print("Trying turbo model...")
    url_fallback = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=turbo&seed={seed}&nologo=true"
    response = requests.get(url_fallback, timeout=60)

    if response.status_code == 200 and len(response.content) > 5000:
        print(f"Image generated (turbo): {len(response.content)/1024:.1f} KB")
        return response.content

    raise Exception(f"Image generation failed: status {response.status_code}")


#----------------------------------------------------------------
# UPLOAD TO IMGBB
#----------------------------------------------------------------

def upload_to_imgbb(image_bytes):
    """Upload generated image to imgbb for permanent public URL"""
    print("Uploading to imgbb...")
    response = requests.post(
        'https://api.imgbb.com/1/upload',
        params={'key': os.getenv('IMGBB_API_KEY')},
        files={'image': image_bytes}
    )
    result = response.json()
    if result['success']:
        url = result['data']['url']
        print(f"Hosted: {url}")
        return url
    raise Exception(f"imgbb upload failed: {result}")


#----------------------------------------------------------------
# SAVE AS DRAFT
#----------------------------------------------------------------

def save_as_draft(image_url, caption, prompt, tone='casual'):
    """Save generated image as a draft for preview"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        '''INSERT INTO drafts (image_url, caption, tone, media_type, status)
           VALUES (?, ?, ?, "IMAGE", "PENDING")''',
        (image_url, caption, tone)
    )
    draft_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return draft_id


#----------------------------------------------------------------
# MAIN
#----------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate-image.py 'image description' [tone]")
        sys.exit(1)

    prompt = sys.argv[1]
    tone = sys.argv[2] if len(sys.argv) > 2 else 'casual'

    try:
        # Step 1 — Generate image
        image_bytes = generate_image(prompt)

        # Step 2 — Upload to imgbb
        image_url = upload_to_imgbb(image_bytes)

        # Step 3 — Generate caption using AI Router
        print("Generating caption with AI Router...")
        caption_prompt = f"""Generate an Instagram caption for an AI-generated image of: "{prompt}"
Tone: {tone}
Requirements:
1. Mention it is AI-generated art
2. 2-3 sentences, engaging
3. 5-7 relevant hashtags
4. Call to action
Return only caption and hashtags."""

        caption = generate_text(caption_prompt, max_tokens=300)
        print(f"Caption generated.")

        # Step 4 — Save as draft
        draft_id = save_as_draft(image_url, caption, prompt, tone)

        print(f"\nDRAFT_ID:{draft_id}")
        print(f"IMAGE_URL:{image_url}")
        print(f"PROMPT:{prompt}")
        print(f"CAPTION:{caption}")

    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
