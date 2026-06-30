#!/usr/bin/env python3
"""
Instagram Post Pipeline with AI-Generated Captions
Generates captions using Anthropic Claude and posts to Instagram via Composio.
Supports both IMAGE and VIDEO content types.
Usage: python3 post-with-caption.py [URL] [TONE]
"""

import os
import sys
import time
import requests
import anthropic
from dotenv import load_dotenv

load_dotenv()

#----------------------------------------------------------------
# CAPTION GENERATION — Anthropic Claude
#----------------------------------------------------------------

def generate_caption(url, tone='casual', Type="IMAGE"):
    """Generate Instagram caption using Claude"""
    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            messages=[{
                'role': 'user',
                'content': f'''Generate an Instagram caption for this {Type.lower()}: "{url}".
Tone: {tone}

Requirements:
1. Instagram Caption max 2-3 sentences, engaging and authentic
2. 5-7 relevant hashtags
3. A call to action

Return only the caption and hashtags, nothing else.'''
            }]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"Caption generation error: {e}")
        return f"Exploring new horizons! #Innovation #Technology #IoT"

#----------------------------------------------------------------
# IMAGE HOSTING — imgbb (required for Instagram image API)
#----------------------------------------------------------------

def upload_to_imgbb(image_url):
    """Upload image to imgbb and return a public direct URL"""
    try:
        img_data = requests.get(image_url).content
        response = requests.post(
            'https://api.imgbb.com/1/upload',
            params={'key': os.getenv('IMGBB_API_KEY')},
            files={'image': img_data}
        )
        result = response.json()
        if result['success']:
            return result['data']['url']
        raise Exception(f"imgbb upload failed: {result}")
    except Exception as e:
        print(f"imgbb upload error: {e} — using original URL")
        return image_url

#----------------------------------------------------------------
# INSTAGRAM POSTING — Composio MCP
#----------------------------------------------------------------

def post_to_instagram(url, caption, Type):
    """Post image or video to Instagram using Composio"""
    try:
        from composio import Composio

        api_key = os.getenv('COMPOSIO_API_KEY')
        if not api_key:
            raise ValueError("COMPOSIO_API_KEY not set in environment")

        client = Composio(api_key=api_key)
        accounts = client.connected_accounts.list()
        items = dict(accounts)['items']

        if not items:
            raise ValueError("No Instagram account connected in Composio")

        user_id = items[0].user_id
        connected_account_id = items[0].id
        ig_user_id = os.getenv('INSTAGRAM_USER_ID')

        if not ig_user_id:
            raise ValueError("INSTAGRAM_USER_ID not set in environment")

        print(f"Posting {Type} to Instagram...")

        # Step 1 — Create media container
        step1 = client.tools.execute(
            slug='INSTAGRAM_CREATE_MEDIA_CONTAINER',
            arguments={
                ("image_url" if Type == "IMAGE" else "video_url"): url,
                "caption": caption,
                "media_type": Type,
                "content_type": "reel" if Type == "VIDEO" else "photo",
                "ig_user_id": ig_user_id
            },
            connected_account_id=connected_account_id,
            user_id=user_id,
            dangerously_skip_version_check=True
        )

        if not step1['successful']:
            raise Exception(f"Container creation failed: {step1.get('error', 'Unknown error')}")

        creation_id = step1['data']['id']
        print(f"Container created: {creation_id}")

        # Step 2 — Publish
        step2 = client.tools.execute(
            slug='INSTAGRAM_CREATE_POST',
            arguments={
                'ig_user_id': ig_user_id,
                'creation_id': creation_id
            },
            connected_account_id=connected_account_id,
            user_id=user_id,
            dangerously_skip_version_check=True
        )

        if not step2['successful']:
            raise Exception(f"Publishing failed: {step2.get('error', 'Unknown error')}")

        return step2['data']['id']

    except ImportError as e:
        raise ValueError(f"Composio package not found: {e}")

#----------------------------------------------------------------
# MAIN
#----------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 post-with-caption.py [URL] [TONE]")
        sys.exit(1)

    url = sys.argv[1]
    tone = sys.argv[2] if len(sys.argv) > 2 else "casual"

    try:
        # Auto-detect IMAGE vs VIDEO
        print("Detecting media type...")
        r = requests.head(url, allow_redirects=True)
        content_type = r.headers.get("Content-Type", "")
        print(f"Content-Type: {content_type}")

        if content_type.startswith("video/"):
            Type = "VIDEO"
            print("Detected: VIDEO")

        elif content_type.startswith("image/"):
            Type = "IMAGE"
            print("Detected: IMAGE")
            print("Uploading to imgbb...")
            url = upload_to_imgbb(url)
            print(f"Hosted URL: {url}")

        else:
            Type = "IMAGE"
            print(f"Unknown content type — defaulting to IMAGE")
            print("Uploading to imgbb...")
            url = upload_to_imgbb(url)
            print(f"Hosted URL: {url}")

        # Generate caption
        print("Generating caption with Claude...")
        caption = generate_caption(url, tone, Type)
        print(f"\nGenerated Caption:\n{caption}\n")

        # Post to Instagram
        post_id = post_to_instagram(url, caption, Type)
        print(f"\nSUCCESS! Post ID: {post_id}")
        print(f"Check: https://instagram.com/iot_academy_projects")

    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
