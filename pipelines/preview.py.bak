#!/usr/bin/env python3
"""
Preview Pipeline — Generate caption and save as draft before posting
Usage:
  python3 pipelines/preview.py create [url] [tone]     — create a draft
  python3 pipelines/preview.py approve [draft_id]      — post the draft
  python3 pipelines/preview.py reject [draft_id]       — delete the draft
  python3 pipelines/preview.py update [draft_id] [new_caption] — update caption
"""

import sys
import os
import requests
import sqlite3
sys.path.insert(0, '/teamspace/studios/this_studio/uct-insta-agent')
from dotenv import load_dotenv
load_dotenv('/teamspace/studios/this_studio/uct-insta-agent/.env')
from pipelines.ai_router import generate_caption, log_post

DB_PATH = '/teamspace/studios/this_studio/uct-insta-agent/db/uct_agent.sqlite'

#----------------------------------------------------------------
# DRAFT MANAGEMENT
#----------------------------------------------------------------

def create_draft(image_url, tone='casual'):
    """Download image, generate caption, save as PENDING draft"""

    # Detect media type
    r = requests.head(image_url, allow_redirects=True)
    content_type = r.headers.get("Content-Type", "")
    media_type = "VIDEO" if content_type.startswith("video/") else "IMAGE"

    # Upload image to imgbb if IMAGE
    hosted_url = image_url
    if media_type == "IMAGE":
        print("Uploading to imgbb...")
        img_data = requests.get(image_url).content
        response = requests.post(
            'https://api.imgbb.com/1/upload',
            params={'key': os.getenv('IMGBB_API_KEY')},
            files={'image': img_data}
        )
        result = response.json()
        if result['success']:
            hosted_url = result['data']['url']
            print(f"Hosted: {hosted_url}")

    # Generate caption
    print("Generating caption with AI Router...")
    caption = generate_caption(hosted_url, tone, media_type)
    print(f"Caption generated.")

    # Save draft to DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        '''INSERT INTO drafts (image_url, caption, tone, media_type, status)
           VALUES (?, ?, ?, ?, "PENDING")''',
        (hosted_url, caption, tone, media_type)
    )
    draft_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"\nDRAFT_ID:{draft_id}")
    print(f"MEDIA_TYPE:{media_type}")
    print(f"IMAGE_URL:{hosted_url}")
    print(f"CAPTION:{caption}")
    return draft_id, hosted_url, caption, media_type


def approve_draft(draft_id):
    """Post the draft to Instagram and mark as POSTED"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        'SELECT image_url, caption, tone, media_type FROM drafts WHERE id = ? AND status = "PENDING"',
        (draft_id,)
    ).fetchone()
    conn.close()

    if not row:
        print(f"FAILED: Draft {draft_id} not found or already processed.")
        return

    image_url, caption, tone, media_type = row

    # Post to Instagram
    from composio import Composio
    client = Composio(api_key=os.getenv('COMPOSIO_API_KEY'))
    accounts = client.connected_accounts.list()
    items = dict(accounts)['items']
    user_id = items[0].user_id
    connected_account_id = items[0].id
    ig_user_id = os.getenv('INSTAGRAM_USER_ID')

    step1 = client.tools.execute(
        slug='INSTAGRAM_CREATE_MEDIA_CONTAINER',
        arguments={
            ("image_url" if media_type == "IMAGE" else "video_url"): image_url,
            "caption": caption,
            "media_type": media_type,
            "content_type": "reel" if media_type == "VIDEO" else "photo",
            "ig_user_id": ig_user_id
        },
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )

    if not step1['successful']:
        print(f"FAILED: {step1.get('error')}")
        return

    creation_id = step1['data']['id']
    step2 = client.tools.execute(
        slug='INSTAGRAM_CREATE_POST',
        arguments={'ig_user_id': ig_user_id, 'creation_id': creation_id},
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )

    if not step2['successful']:
        print(f"FAILED: {step2.get('error')}")
        return

    post_id = step2['data']['id']

    # Update draft status
    conn = sqlite3.connect(DB_PATH)
    conn.execute('UPDATE drafts SET status = "POSTED" WHERE id = ?', (draft_id,))
    conn.execute(
        '''INSERT OR IGNORE INTO posts
           (post_id, caption, media_type, tone, image_url, provider)
           VALUES (?, ?, ?, ?, ?, "composio")''',
        (post_id, caption, media_type, tone, image_url)
    )
    conn.commit()
    conn.close()

    print(f"SUCCESS! Post ID: {post_id}")
    print(f"Check: https://instagram.com/iot_academy_projects")


def reject_draft(draft_id):
    """Delete a pending draft"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute('DELETE FROM drafts WHERE id = ?', (draft_id,))
    conn.commit()
    conn.close()
    print(f"Draft {draft_id} cancelled and deleted.")


def update_draft_caption(draft_id, new_caption):
    """Update the caption of a pending draft"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'UPDATE drafts SET caption = ? WHERE id = ? AND status = "PENDING"',
        (new_caption, draft_id)
    )
    conn.commit()

    # Return updated draft
    row = conn.execute(
        'SELECT image_url, caption, media_type FROM drafts WHERE id = ?',
        (draft_id,)
    ).fetchone()
    conn.close()

    if row:
        image_url, caption, media_type = row
        print(f"UPDATED_ID:{draft_id}")
        print(f"IMAGE_URL:{image_url}")
        print(f"CAPTION:{caption}")
        print(f"MEDIA_TYPE:{media_type}")
    else:
        print(f"FAILED: Draft {draft_id} not found.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: preview.py [create|approve|reject|update] [args]")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'create':
        url = sys.argv[2] if len(sys.argv) > 2 else None
        tone = sys.argv[3] if len(sys.argv) > 3 else 'casual'
        if not url:
            print("FAILED: URL required")
            sys.exit(1)
        create_draft(url, tone)

    elif command == 'approve':
        draft_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        if not draft_id:
            print("FAILED: Draft ID required")
            sys.exit(1)
        approve_draft(draft_id)

    elif command == 'reject':
        draft_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        if not draft_id:
            print("FAILED: Draft ID required")
            sys.exit(1)
        reject_draft(draft_id)

    elif command == 'update':
        draft_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        new_caption = sys.argv[3] if len(sys.argv) > 3 else None
        if not draft_id or not new_caption:
            print("FAILED: Draft ID and new caption required")
            sys.exit(1)
        update_draft_caption(draft_id, new_caption)

    else:
        print(f"Unknown command: {command}")
