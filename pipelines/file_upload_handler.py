#!/usr/bin/env python3
"""
File Upload Handler — processes files sent directly via Telegram
Usage: python3 pipelines/file_upload_handler.py [file_path] [tone]
"""

import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
import sqlite3
import requests
import base64
sys.path.insert(0, PROJECT_ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
from pipelines.ai_router import generate_text, describe_image

DB_PATH = os.path.join(PROJECT_ROOT, 'db', 'uct_agent.sqlite')

def upload_file_to_imgbb(file_path):
    """Upload a local file to imgbb and return public URL"""
    print(f"Uploading file: {os.path.basename(file_path)}")
    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    response = requests.post(
        "https://api.imgbb.com/1/upload",
        params={"key": os.getenv("IMGBB_API_KEY")},
        data={"image": image_data}
    )
    result = response.json()
    if result["success"]:
        url = result["data"]["url"]
        print(f"Hosted: {url}")
        return url
    raise Exception(f"imgbb upload failed: {result}")

def detect_media_type(file_path):
    """Detect if file is image or video based on extension"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".mp4", ".mov", ".avi", ".mkv"]:
        return "VIDEO"
    return "IMAGE"

def generate_caption_for_file(media_type, tone="casual", description=None):
    """Generate caption based on real image content (via vision) or a
    user-provided description — not just the filename, which carries no
    information about what's actually in the file."""

    prompt = f"""Generate an Instagram caption for this {media_type.lower()}: "{description}"
Tone: {tone}

Requirements:
1. 2-3 sentences, engaging and authentic
2. 5-7 relevant hashtags
3. Call to action

Return only caption and hashtags."""

    return generate_text(prompt, max_tokens=300)

def save_draft(image_url, caption, tone, media_type):
    """Save as pending draft"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """INSERT INTO drafts (image_url, caption, tone, media_type, status)
           VALUES (?, ?, ?, ?, "PENDING")""",
        (image_url, caption, tone, media_type)
    )
    draft_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return draft_id

def main():
    if len(sys.argv) < 2:
        print("Usage: file_upload_handler.py [file_path] [tone] [description]")
        print("  DESCRIPTION is optional — if omitted, the image is described")
        print("  automatically via vision before the caption is written.")
        sys.exit(1)

    file_path = sys.argv[1]
    tone = sys.argv[2] if len(sys.argv) > 2 else "casual"
    user_description = sys.argv[3] if len(sys.argv) > 3 else None

    if not os.path.exists(file_path):
        print(f"FAILED: File not found: {file_path}")
        sys.exit(1)

    file_size = os.path.getsize(file_path)
    print(f"File size: {file_size/1024:.1f} KB")

    media_type = detect_media_type(file_path)
    print(f"Media type: {media_type}")

    # Upload to imgbb FIRST — vision needs a public URL to look at,
    # so this must happen before caption generation, not after.
    image_url = upload_file_to_imgbb(file_path)

    # Generate caption
    print("Generating caption...")
    if user_description:
        description = user_description
        print(f"Using provided description: {description}")
    elif media_type == "IMAGE":
        print("Describing image with vision...")
        description = describe_image(image_url) or "an interesting photo"
    else:
        # Vision model here is image-only; video falls back to generic
        description = "an engaging video"
    caption = generate_caption_for_file(media_type, tone, description)
    print(f"Caption generated.")

    # Save as draft
    draft_id = save_draft(image_url, caption, tone, media_type)

    print(f"\nDRAFT_ID:{draft_id}")
    print(f"MEDIA_TYPE:{media_type}")
    print(f"IMAGE_URL:{image_url}")
    print(f"CAPTION:{caption}")

if __name__ == "__main__":
    main()