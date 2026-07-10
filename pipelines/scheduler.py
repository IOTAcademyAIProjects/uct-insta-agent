#!/usr/bin/env python3
"""
M10 - Stories & Advanced Scheduling Pipeline
Usage:
  python3 scheduler.py story [url]           - post a story now
  python3 scheduler.py schedule [url] [datetime] [tone] - schedule a post
  python3 scheduler.py list                  - list scheduled posts
  python3 scheduler.py run                   - run scheduler (check and publish due posts)
  python3 scheduler.py cancel [id]           - cancel a scheduled post
"""

import os
import sys
import time
import sqlite3
import requests
from datetime import datetime, timezone
sys.path.insert(0, "/teamspace/studios/this_studio/uct-insta-agent")
from dotenv import load_dotenv
load_dotenv("/teamspace/studios/this_studio/uct-insta-agent/.env")
from composio import Composio
from pipelines.ai_router import generate_caption

DB_PATH = "/teamspace/studios/this_studio/uct-insta-agent/db/uct_agent.sqlite"

#----------------------------------------------------------------
# DB SETUP
#----------------------------------------------------------------

def setup_scheduler_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT,
            caption TEXT,
            tone TEXT,
            media_type TEXT DEFAULT "IMAGE",
            post_type TEXT DEFAULT "FEED",
            scheduled_time DATETIME,
            status TEXT DEFAULT "PENDING",
            post_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

#----------------------------------------------------------------
# COMPOSIO CLIENT
#----------------------------------------------------------------

def get_client():
    client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))
    accounts = client.connected_accounts.list()
    items = dict(accounts)["items"]
    user_id = items[0].user_id
    connected_account_id = items[0].id
    ig_user_id = os.getenv("INSTAGRAM_USER_ID")
    return client, user_id, connected_account_id, ig_user_id

#----------------------------------------------------------------
# IMGBB UPLOAD
#----------------------------------------------------------------

def upload_to_imgbb(image_url):
    img_data = requests.get(image_url).content
    response = requests.post(
        "https://api.imgbb.com/1/upload",
        params={"key": os.getenv("IMGBB_API_KEY")},
        files={"image": img_data}
    )
    result = response.json()
    if result["success"]:
        return result["data"]["url"]
    raise Exception(f"imgbb upload failed: {result}")

#----------------------------------------------------------------
# STORY POSTING
#----------------------------------------------------------------

def post_story(image_url):
    print("Uploading image to imgbb...")
    hosted_url = upload_to_imgbb(image_url)
    print(f"Hosted: {hosted_url}")

    client, user_id, connected_account_id, ig_user_id = get_client()

    print("Creating story container...")
    step1 = client.tools.execute(
        slug="INSTAGRAM_CREATE_MEDIA_CONTAINER",
        arguments={
            "image_url": hosted_url,
            "media_type": "STORIES",
            "ig_user_id": ig_user_id
        },
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not step1["successful"]:
        raise Exception(f"Story container failed: {step1.get('error')}")

    creation_id = step1["data"]["id"]
    print(f"Container created: {creation_id}")

    print("Publishing story...")
    step2 = client.tools.execute(
        slug="INSTAGRAM_CREATE_POST",
        arguments={"ig_user_id": ig_user_id, "creation_id": creation_id},
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not step2["successful"]:
        raise Exception(f"Story publish failed: {step2.get('error')}")

    post_id = step2["data"]["id"]
    print(f"SUCCESS! Story ID: {post_id}")
    print(f"Check: https://instagram.com/iot_academy_projects")
    return post_id

#----------------------------------------------------------------
# SCHEDULING
#----------------------------------------------------------------

def schedule_post(image_url, scheduled_time_str, tone="casual", media_type="IMAGE", post_type="FEED"):
    setup_scheduler_table()

    # Upload image now to get permanent URL
    print("Uploading image to imgbb for scheduling...")
    hosted_url = upload_to_imgbb(image_url)
    print(f"Hosted: {hosted_url}")

    # Generate caption now
    print("Generating caption with AI Router...")
    caption = generate_caption(hosted_url, tone, media_type)
    print(f"Caption generated.")

    # Parse scheduled time
    try:
        scheduled_dt = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            scheduled_dt = datetime.strptime(scheduled_time_str, "%Y-%m-%d")
            scheduled_dt = scheduled_dt.replace(hour=9, minute=0)
        except ValueError:
            raise Exception(f"Invalid date format. Use: YYYY-MM-DD HH:MM or YYYY-MM-DD")

    # Save to DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """INSERT INTO scheduled_posts
           (image_url, caption, tone, media_type, post_type, scheduled_time, status)
           VALUES (?, ?, ?, ?, ?, ?, "PENDING")""",
        (hosted_url, caption, tone, media_type, post_type, scheduled_dt.strftime("%Y-%m-%d %H:%M:%S"))
    )
    schedule_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"\nSCHEDULED! ID: {schedule_id}")
    print(f"Post time: {scheduled_dt.strftime('%Y-%m-%d %H:%M')}")
    print(f"Type: {post_type} | Tone: {tone}")
    print(f"Caption preview: {caption[:80]}...")
    return schedule_id

#----------------------------------------------------------------
# LIST SCHEDULED POSTS
#----------------------------------------------------------------

def list_scheduled():
    setup_scheduler_table()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        """SELECT id, scheduled_time, post_type, media_type, tone, status, caption
           FROM scheduled_posts
           ORDER BY scheduled_time ASC"""
    ).fetchall()
    conn.close()

    if not rows:
        print("No scheduled posts.")
        return

    print(f"Scheduled posts ({len(rows)} total):\n")
    for row in rows:
        id_, stime, ptype, mtype, tone, status, caption = row
        caption_preview = (caption or "")[:60] + "..." if len(caption or "") > 60 else caption
        emoji = "✅" if status == "POSTED" else "⏳" if status == "PENDING" else "❌"
        print(f"[{id_}] {emoji} {stime} | {ptype} | {mtype} | {tone}")
        print(f"     {caption_preview}")
        print()

#----------------------------------------------------------------
# CANCEL SCHEDULED POST
#----------------------------------------------------------------

def cancel_scheduled(post_id):
    setup_scheduler_table()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE scheduled_posts SET status = 'CANCELLED' WHERE id = ? AND status = 'PENDING'",
        (post_id,)
    )
    conn.commit()
    conn.close()
    print(f"Scheduled post {post_id} cancelled.")

#----------------------------------------------------------------
# RUN SCHEDULER - publish due posts
#----------------------------------------------------------------

def publish_post(image_url, caption, media_type, post_type):
    client, user_id, connected_account_id, ig_user_id = get_client()

    if post_type == "STORY":
        container_type = "STORIES"
    else:
        container_type = media_type

    step1 = client.tools.execute(
        slug="INSTAGRAM_CREATE_MEDIA_CONTAINER",
        arguments={
            "image_url": image_url,
            "caption": caption if post_type != "STORY" else None,
            "media_type": container_type,
            "content_type": "photo",
            "ig_user_id": ig_user_id
        },
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not step1["successful"]:
        raise Exception(f"Container failed: {step1.get('error')}")

    creation_id = step1["data"]["id"]
    step2 = client.tools.execute(
        slug="INSTAGRAM_CREATE_POST",
        arguments={"ig_user_id": ig_user_id, "creation_id": creation_id},
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not step2["successful"]:
        raise Exception(f"Publish failed: {step2.get('error')}")

    return step2["data"]["id"]


def run_scheduler():
    setup_scheduler_table()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    due_posts = conn.execute(
        """SELECT id, image_url, caption, media_type, post_type
           FROM scheduled_posts
           WHERE status = "PENDING" AND scheduled_time <= ?""",
        (now,)
    ).fetchall()
    conn.close()

    if not due_posts:
        print(f"No posts due at {now}")
        return

    print(f"Found {len(due_posts)} post(s) due for publishing...")

    for row in due_posts:
        post_id_db, image_url, caption, media_type, post_type = row
        try:
            print(f"Publishing scheduled post {post_id_db}...")
            post_id = publish_post(image_url, caption, media_type, post_type)

            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "UPDATE scheduled_posts SET status = 'POSTED', post_id = ? WHERE id = ?",
                (post_id, post_id_db)
            )
            conn.commit()
            conn.close()

            print(f"SUCCESS! Post ID: {post_id}")

            # Send Telegram notification
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = "8909720609"
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"Scheduled post published!\nPost ID: {post_id}\nCheck: https://instagram.com/iot_academy_projects"
                }
            )

        except Exception as e:
            print(f"FAILED post {post_id_db}: {e}")
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "UPDATE scheduled_posts SET status = 'FAILED' WHERE id = ?",
                (post_id_db,)
            )
            conn.commit()
            conn.close()

#----------------------------------------------------------------
# MAIN
#----------------------------------------------------------------

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "story":
        url = sys.argv[2] if len(sys.argv) > 2 else None
        if not url:
            print("Usage: scheduler.py story [url]")
        else:
            post_story(url)

    elif cmd == "schedule":
        if len(sys.argv) < 4:
            print("Usage: scheduler.py schedule [url] [YYYY-MM-DD HH:MM] [tone]")
        else:
            url = sys.argv[2]
            scheduled_time = sys.argv[3]
            tone = sys.argv[4] if len(sys.argv) > 4 else "casual"
            schedule_post(url, scheduled_time, tone)

    elif cmd == "list":
        list_scheduled()

    elif cmd == "run":
        run_scheduler()

    elif cmd == "cancel":
        post_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        if post_id:
            cancel_scheduled(post_id)
        else:
            print("Usage: scheduler.py cancel [id]")

    else:
        print(f"Unknown: {cmd}")
        print("Commands: story [url], schedule [url] [datetime] [tone], list, run, cancel [id]")
