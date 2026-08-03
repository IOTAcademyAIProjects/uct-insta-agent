#!/usr/bin/env python3
"""
Instagram Post Pipeline — Multi-AI Router Edition
No Claude/Anthropic needed. Uses NVIDIA, Cerebras, Mistral in rotation.
Usage: python3 post-with-caption.py [URL] [TONE]
"""

import os
import sys
import requests
from dotenv import load_dotenv
load_dotenv('/teamspace/studios/this_studio/uct-insta-agent/.env')

# Import AI router instead of Claude
sys.path.insert(0, '/teamspace/studios/this_studio/uct-insta-agent')
from pipelines.ai_router import generate_caption, describe_image
from pipelines.ig_connection import get_instagram_client

def upload_to_imgbb(image_url):
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

def post_to_instagram(url, caption, Type):
    client, user_id, connected_account_id, ig_user_id = get_instagram_client()

    # Composio's INSTAGRAM_CREATE_MEDIA_CONTAINER schema: for plain image
    # posts, media_type must be OMITTED entirely (image is the default).
    # Sending media_type: "IMAGE" is invalid and gets rejected. Only VIDEO
    # posts need media_type explicitly set to "REELS".
    container_args = {
        ("image_url" if Type == "IMAGE" else "video_url"): url,
        "caption": caption,
        "content_type": "reel" if Type == "VIDEO" else "photo",
        "ig_user_id": ig_user_id
    }
    if Type == "VIDEO":
        container_args["media_type"] = "REELS"

    step1 = client.tools.execute(
        slug='INSTAGRAM_CREATE_MEDIA_CONTAINER',
        arguments=container_args,
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not step1['successful']:
        raise Exception(f"Container failed: {step1.get('error')}")

    creation_id = step1['data']['id']
    step2 = client.tools.execute(
        slug='INSTAGRAM_CREATE_POST',
        arguments={'ig_user_id': ig_user_id, 'creation_id': creation_id},
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not step2['successful']:
        raise Exception(f"Publish failed: {step2.get('error')}")
    return step2['data']['id']

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 post-with-caption.py [URL] [TONE] [DESCRIPTION]")
        print("  DESCRIPTION is optional — if omitted, the image is described")
        print("  automatically via vision before the caption is written.")
        sys.exit(1)

    url = sys.argv[1]
    tone = sys.argv[2] if len(sys.argv) > 2 else "casual"
    user_description = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        print("Detecting media type...")
        r = requests.head(url, allow_redirects=True)
        content_type = r.headers.get("Content-Type", "")

        if content_type.startswith("video/"):
            Type = "VIDEO"
            print("Detected: VIDEO")
        else:
            Type = "IMAGE"
            print("Detected: IMAGE")
            print("Uploading to imgbb...")
            url = upload_to_imgbb(url)
            print(f"Hosted: {url}")

        print("Generating caption with AI Router...")
        if user_description:
            description = user_description
            print(f"Using provided description: {description}")
        elif Type == "IMAGE":
            print("Describing image with vision...")
            description = describe_image(url) or "an interesting photo"
        else:
            # Vision model here is image-only; video falls back to generic
            description = "an engaging video"
        caption = generate_caption(description, tone, Type)
        print(f"\nCaption:\n{caption}\n")

        print("Posting to Instagram...")
        post_id = post_to_instagram(url, caption, Type)
        print(f"\nSUCCESS! Post ID: {post_id}")
        print(f"Check: https://instagram.com/iot_academy_projects")

    except Exception as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()