#!/usr/bin/env python3
"""
Instagram Post Pipeline with AI-Generated Captions

Generates captions using Claude AI and posts to Instagram via Composio.
Usage: python3 post-with-caption.py IMAGE_URL DESCRIPTION TONE
"""

import sys
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_caption(image_description, tone='casual'):
    """Generate Instagram caption using Claude API"""
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        prompt = f"""Generate an Instagram caption for an image. 
        
Image Description: {image_description}
Tone: {tone}

Requirements:
- 1-3 sentences, engaging and authentic
- Include 3-5 relevant hashtags
- Keep it conversational but aligned with the {tone} tone
- Don't use emojis unless they naturally fit the tone

Return ONLY the caption text with hashtags, nothing else."""

        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=150,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text.strip()
    
    except ImportError:
        # Fallback if anthropic package not available
        print("WARNING: Anthropic package not found, using default caption")
        return f"Check out this {tone.lower()} moment! 📸 #photography"

def post_to_instagram(image_url, caption):
    """Post to Instagram using Composio"""
    try:
        from composio import Composio
        
        api_key = os.getenv('COMPOSIO_API_KEY')
        if not api_key:
            raise ValueError("COMPOSIO_API_KEY not set in environment")
        
        client = Composio(api_key=api_key)
        
        # Get connected account info
        accounts = client.connected_accounts.list()
        items = dict(accounts)['items']
        
        if not items:
            raise ValueError("No Instagram account connected in Composio")
        
        user_id = items[0].user_id
        connected_account_id = items[0].id
        ig_user_id = os.getenv('INSTAGRAM_USER_ID')
        
        if not ig_user_id:
            raise ValueError("INSTAGRAM_USER_ID not set in environment")
        
        # Step 1: Create media container
        step1 = client.tools.execute(
            slug='INSTAGRAM_CREATE_MEDIA_CONTAINER',
            arguments={
                'image_url': image_url,
                'caption': caption,
                'media_type': 'IMAGE',
                'ig_user_id': ig_user_id
            },
            connected_account_id=connected_account_id,
            user_id=user_id,
            dangerously_skip_version_check=True
        )
        
        if not step1['successful']:
            raise Exception(f"Failed to create container: {step1.get('error', 'Unknown error')}")
        
        creation_id = step1['data']['id']
        
        # Step 2: Publish
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
            raise Exception(f"Failed to publish: {step2.get('error', 'Unknown error')}")
        
        post_id = step2['data']['id']
        return post_id
        
    except ImportError as e:
        raise ValueError(f"Composio package not found: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 post-with-caption.py IMAGE_URL [DESCRIPTION] [TONE]")
        sys.exit(1)
    
    image_url = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else "a beautiful image"
    tone = sys.argv[3] if len(sys.argv) > 3 else "casual"
    
    try:
        # Validate tone
        valid_tones = ['casual', 'inspirational', 'professional', 'funny']
        if tone not in valid_tones:
            tone = 'casual'
        
        # Generate caption
        print(f"Generating {tone} caption for: {description}", file=sys.stderr)
        caption = generate_caption(description, tone)
        print(f"Generated caption: {caption}", file=sys.stderr)
        
        # Post to Instagram
        print("Posting to Instagram...", file=sys.stderr)
        post_id = post_to_instagram(image_url, caption)
        
        # Print success
        print("SUCCESS")
        print(f"Post ID: {post_id}")
        print(f"URL: https://instagram.com/iot_academy_projects")
        
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        print(f"FAILED: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
