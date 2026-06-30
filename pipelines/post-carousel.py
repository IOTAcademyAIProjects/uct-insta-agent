#!/usr/bin/env python3
"""
Instagram Carousel Post Pipeline
Posts 2-10 images as a single Instagram carousel with an AI-generated caption.
Usage: python3 post-carousel.py "url1,url2,url3" "tone"
"""

import os
import sys
import requests
import anthropic
from dotenv import load_dotenv

load_dotenv()

#----------------------------------------------------------------
# CAPTION GENERATION
#----------------------------------------------------------------

def generate_caption(image_count, tone='casual'):
    """Generate a unified caption for the whole carousel"""
    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            messages=[{
                'role': 'user',
                'content': f'''Generate an Instagram caption for a carousel post with {image_count} images.
Tone: {tone}

Requirements:
1. Caption max 2-3 sentences, engaging and authentic
2. Mention it's a series/collection if relevant
3. 5-7 relevant hashtags
4. A call to action (e.g. swipe to see more)

Return only the caption and hashtags, nothing else.'''
            }]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"Caption generation error: {e}")
        return f"A collection worth swiping through. #Photography #Series #Moments"

#----------------------------------------------------------------
# IMAGE HOSTING
#----------------------------------------------------------------

def upload_to_imgbb(image_url):
    """Upload a single image to imgbb, return direct URL"""
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

#----------------------------------------------------------------
# CAROUSEL POSTING — Composio
#----------------------------------------------------------------

def post_carousel(image_urls, caption):
    """Create carousel children, then carousel container, then publish"""
    from composio import Composio

    api_key = os.getenv('COMPOSIO_API_KEY')
    client = Composio(api_key=api_key)
    accounts = client.connected_accounts.list()
    items = dict(accounts)['items']

    if not items:
        raise ValueError("No Instagram account connected in Composio")

    user_id = items[0].user_id
    connected_account_id = items[0].id
    ig_user_id = os.getenv('INSTAGRAM_USER_ID')

    if len(image_urls) < 2 or len(image_urls) > 10:
        raise ValueError("Carousel requires between 2 and 10 images")

    # Step 1 — create a child media container for each image
    child_ids = []
    for i, url in enumerate(image_urls):
        print(f"Creating child container {i+1}/{len(image_urls)}...")
        result = client.tools.execute(
            slug='INSTAGRAM_CREATE_MEDIA_CONTAINER',
            arguments={
                'image_url': url,
                'media_type': 'IMAGE',
                'is_carousel_item': True,
                'ig_user_id': ig_user_id
            },
            connected_account_id=connected_account_id,
            user_id=user_id,
            dangerously_skip_version_check=True
        )
        if not result['successful']:
            raise Exception(f"Child container {i+1} failed: {result.get('error')}")
        child_ids.append(result['data']['id'])
        print(f"Child {i+1} created: {result['data']['id']}")

    # Step 2 — create the carousel container referencing all children
    print("Creating carousel container...")
    carousel_result = client.tools.execute(
        slug='INSTAGRAM_CREATE_CAROUSEL_CONTAINER',
        arguments={
            'ig_user_id': ig_user_id,
            'caption': caption,
            'children': child_ids
        },
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not carousel_result['successful']:
        raise Exception(f"Carousel container failed: {carousel_result.get('error')}")

    carousel_creation_id = carousel_result['data']['id']
    print(f"Carousel container created: {carousel_creation_id}")

    # Step 3 — publish
    print("Publishing carousel...")
    publish_result = client.tools.execute(
        slug='INSTAGRAM_CREATE_POST',
        arguments={
            'ig_user_id': ig_user_id,
            'creation_id': carousel_creation_id
        },
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not publish_result['successful']:
        raise Exception(f"Carousel publish failed: {publish_result.get('error')}")

    return publish_result['data']['id']

#----------------------------------------------------------------
# MAIN
#----------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 post-carousel.py 'url1,url2,url3' [tone]")
        sys.exit(1)

    raw_urls = sys.argv[1]
    tone = sys.argv[2] if len(sys.argv) > 2 else "casual"

    image_urls = [u.strip() for u in raw_urls.split(',') if u.strip()]

    if len(image_urls) < 2:
        print("FAILED: Carousel needs at least 2 image URLs, comma-separated")
        sys.exit(1)

    try:
        print(f"Preparing carousel with {len(image_urls)} images...")

        # Upload all images to imgbb first
        hosted_urls = []
        for i, url in enumerate(image_urls):
            print(f"Uploading image {i+1}/{len(image_urls)} to imgbb...")
            hosted = upload_to_imgbb(url)
            hosted_urls.append(hosted)
            print(f"Hosted: {hosted}")

        # Generate caption
        print("Generating caption with Claude...")
        caption = generate_caption(len(image_urls), tone)
        print(f"\nGenerated Caption:\n{caption}\n")

        # Post carousel
        post_id = post_carousel(hosted_urls, caption)
        print(f"\nSUCCESS! Carousel Post ID: {post_id}")
        print(f"Check: https://instagram.com/iot_academy_projects")

    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
