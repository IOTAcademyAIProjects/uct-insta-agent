#!/usr/bin/env python3
"""
M7 - DMs & Comments Management + Telegram Notifications
Usage:
  python3 dm-comments.py dms
  python3 dm-comments.py notify
  python3 dm-comments.py conversation [id]
  python3 dm-comments.py comments [post_id]
  python3 dm-comments.py delete [comment_id]
  python3 dm-comments.py summary
"""

import os
import sys
import requests
import sqlite3
sys.path.insert(0, "/teamspace/studios/this_studio/uct-insta-agent")
from dotenv import load_dotenv
load_dotenv("/teamspace/studios/this_studio/uct-insta-agent/.env")
from composio import Composio
from pipelines.ai_router import generate_text

DB_PATH = "/teamspace/studios/this_studio/uct-insta-agent/db/uct_agent.sqlite"

def get_client():
    client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))
    accounts = client.connected_accounts.list()
    items = dict(accounts)["items"]
    user_id = items[0].user_id
    connected_account_id = items[0].id
    ig_user_id = os.getenv("INSTAGRAM_USER_ID")
    return client, user_id, connected_account_id, ig_user_id

def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = "8909720609"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    return r.status_code == 200

def get_seen_dms():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS seen_dms (conversation_id TEXT PRIMARY KEY, seen_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        rows = conn.execute("SELECT conversation_id FROM seen_dms").fetchall()
        conn.close()
        return set(r[0] for r in rows)
    except Exception:
        return set()

def mark_dm_seen(conversation_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS seen_dms (conversation_id TEXT PRIMARY KEY, seen_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("INSERT OR IGNORE INTO seen_dms (conversation_id) VALUES (?)", (conversation_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_dms(limit=10, notify=False):
    client, user_id, connected_account_id, ig_user_id = get_client()
    result = client.tools.execute(
        slug="INSTAGRAM_GET_PAGE_CONVERSATIONS",
        arguments={"page_id": ig_user_id, "platform": "instagram", "limit": limit},
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    conversations = result["data"].get("data", [])
    if not conversations:
        print("No DM conversations found.")
        return []

    seen = get_seen_dms()
    new_count = 0
    print(f"Found {len(conversations)} DM conversation(s):\n")
    for conv in conversations:
        conv_id = conv.get("id")
        updated = conv.get("updated_time", "")[:16].replace("T", " ")
        print(f"Conversation: {conv_id[:40]}...")
        print(f"Updated: {updated}")

        if notify and conv_id not in seen:
            # Fetch full conversation to get message content
            conv_result = client.tools.execute(
                slug="INSTAGRAM_GET_CONVERSATION",
                arguments={"conversation_id": conv_id},
                connected_account_id=connected_account_id,
                user_id=user_id,
                dangerously_skip_version_check=True
            )
            conv_data = conv_result.get("data", {})
            messages = conv_data.get("messages", {}).get("data", [])
            if messages:
                latest = messages[0]
                sender = latest.get("from", {}).get("username", "unknown")
                text = latest.get("message", "")[:200]
                print(f"From: @{sender}")
                print(f"Message: {text}")
                msg = f"\U0001f4e9 New Instagram DM!\n\nFrom: @{sender}\nMessage: {text}\n\nReply via: /dms"
                if send_telegram(msg):
                    print("Telegram notification sent!")
                    mark_dm_seen(conv_id)
                    new_count += 1
        print()

    if notify:
        print(f"New DMs notified: {new_count}")
    return conversations

def get_conversation(conversation_id):
    client, user_id, connected_account_id, ig_user_id = get_client()
    result = client.tools.execute(
        slug="INSTAGRAM_GET_CONVERSATION",
        arguments={"conversation_id": conversation_id},
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    data = result["data"]
    messages = data.get("messages", {}).get("data", [])
    participants = data.get("participants", {}).get("data", [])
    print("Conversation between:")
    for p in participants:
        print(f"  @{p.get('username')}")
    print()
    print("Messages:")
    print("-" * 40)
    for msg in reversed(messages):
        sender = msg.get("from", {}).get("username", "unknown")
        text = msg.get("message", "")
        time = msg.get("created_time", "")[:16].replace("T", " ")
        print(f"[@{sender}] {time}")
        print(f"  {text}")
        print()

def get_comments(post_id, limit=10):
    client, user_id, connected_account_id, ig_user_id = get_client()
    result = client.tools.execute(
        slug="INSTAGRAM_GET_IG_MEDIA_COMMENTS",
        arguments={"ig_media_id": post_id, "fields": "id,text,username,timestamp,like_count", "limit": limit},
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    comments = result["data"].get("data", [])
    if not comments:
        print(f"No comments on post {post_id} yet.")
        return []
    print(f"Found {len(comments)} comment(s):\n")
    for c in comments:
        print(f"[@{c.get('username')}] {c.get('text','')}")
        print(f"  ID: {c.get('id')} | {c.get('timestamp','')[:10]} | Likes: {c.get('like_count',0)}")
        print()
    return comments

def delete_comment(comment_id):
    client, user_id, connected_account_id, ig_user_id = get_client()
    result = client.tools.execute(
        slug="INSTAGRAM_DELETE_COMMENT",
        arguments={"ig_comment_id": comment_id},
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if result["successful"]:
        print(f"Comment {comment_id} deleted.")
    else:
        print(f"Failed: {result.get('error')}")

def get_all_post_comments():
    conn = sqlite3.connect(DB_PATH)
    posts = conn.execute("SELECT post_id FROM posts ORDER BY timestamp DESC LIMIT 5").fetchall()
    conn.close()
    if not posts:
        print("No posts in history yet.")
        return []
    all_comments = []
    for (post_id,) in posts:
        print(f"Checking post {post_id}...")
        comments = get_comments(post_id)
        all_comments.extend(comments)
    return all_comments

def generate_activity_summary():
    convs = get_dms(5)
    comments = get_all_post_comments()
    data = f"DM conversations: {len(convs)}\nComments: {len(comments)}\n"
    for c in comments[:5]:
        data += f"  @{c.get('username')}: {c.get('text','')[:60]}\n"
    prompt = f"Summarize this Instagram engagement for a Telegram message:\n{data}\nWrite 3-4 friendly sentences covering engagement level, notable activity, and one tip."
    summary = generate_text(prompt, max_tokens=300)
    print("\n=== ACTIVITY SUMMARY ===")
    print(summary)
    print("=== END SUMMARY ===")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dms"
    if cmd == "dms":
        get_dms()
    elif cmd == "notify":
        get_dms(notify=True)
    elif cmd == "conversation":
        conv_id = sys.argv[2] if len(sys.argv) > 2 else None
        if conv_id:
            get_conversation(conv_id)
        else:
            print("Usage: dm-comments.py conversation [id]")
    elif cmd == "comments":
        post_id = sys.argv[2] if len(sys.argv) > 2 else None
        if post_id:
            get_comments(post_id)
        else:
            get_all_post_comments()
    elif cmd == "delete":
        comment_id = sys.argv[2] if len(sys.argv) > 2 else None
        if comment_id:
            delete_comment(comment_id)
        else:
            print("Usage: dm-comments.py delete [comment_id]")
    elif cmd == "summary":
        generate_activity_summary()
    else:
        print(f"Unknown: {cmd}")
        print("Commands: dms, notify, conversation [id], comments [post_id], delete [comment_id], summary")
