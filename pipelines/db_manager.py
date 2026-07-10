#!/usr/bin/env python3
"""
Database Manager — handles /storage, /history, /drafts commands
Usage: python3 pipelines/db_manager.py [command] [args]
Commands: storage, history, drafts, delete [id], clear_drafts, clear_history
"""

import sys
import os
sys.path.insert(0, '/teamspace/studios/this_studio/uct-insta-agent')
from pipelines.ai_router import (
    get_storage_stats, get_post_history,
    get_pending_drafts, delete_draft
)
import sqlite3

DB_PATH = '/teamspace/studios/this_studio/uct-insta-agent/db/uct_agent.sqlite'

def cmd_storage():
    stats = get_storage_stats()
    print(f"""
Database Storage Report
=======================
Size:            {stats['size_kb']} KB
Posts logged:    {stats['posts']}
Pending drafts:  {stats['drafts']}
Analytics cache: {stats['analytics_cache']}
AI calls logged: {stats['ai_calls']}
    """.strip())

def cmd_history(limit=10):
    rows = get_post_history(limit)
    if not rows:
        print("No posts in history yet.")
        return
    print(f"Last {len(rows)} posts:\n")
    for row in rows:
        id_, post_id, caption, media_type, provider, timestamp = row
        caption_preview = (caption or '')[:60] + '...' if len(caption or '') > 60 else caption
        print(f"[{id_}] {timestamp[:10]} | {media_type} | {provider}")
        print(f"     Caption: {caption_preview}")
        print(f"     Post ID: {post_id}")
        print()

def cmd_drafts():
    rows = get_pending_drafts()
    if not rows:
        print("No pending drafts.")
        return
    print(f"{len(rows)} pending draft(s):\n")
    for row in rows:
        id_, image_url, caption, tone, media_type, created_at = row
        caption_preview = (caption or '')[:60] + '...' if len(caption or '') > 60 else caption
        print(f"[{id_}] {created_at[:16]} | {media_type} | tone: {tone}")
        print(f"     Caption: {caption_preview}")
        print(f"     URL: {image_url[:60]}")
        print()

def cmd_delete(draft_id):
    success = delete_draft(draft_id)
    if success:
        print(f"Draft {draft_id} deleted successfully.")
    else:
        print(f"Failed to delete draft {draft_id}.")

def cmd_clear_drafts():
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute('SELECT COUNT(*) FROM drafts').fetchone()[0]
    conn.execute('DELETE FROM drafts')
    conn.commit()
    conn.close()
    print(f"Cleared {count} drafts.")

def cmd_clear_history():
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    conn.execute('DELETE FROM posts')
    conn.commit()
    conn.close()
    print(f"Cleared {count} post history entries.")

def cmd_ai_stats():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        '''SELECT provider, COUNT(*) as calls,
           SUM(success) as successful
           FROM ai_calls GROUP BY provider'''
    ).fetchall()
    conn.close()
    if not rows:
        print("No AI calls logged yet.")
        return
    print("AI Provider Stats:\n")
    for provider, calls, successful in rows:
        rate = round((successful/calls)*100) if calls else 0
        print(f"{provider}: {calls} calls, {successful} successful ({rate}% success rate)")

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'storage'

    if cmd == 'storage':
        cmd_storage()
    elif cmd == 'history':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_history(limit)
    elif cmd == 'drafts':
        cmd_drafts()
    elif cmd == 'delete':
        if len(sys.argv) < 3:
            print("Usage: db_manager.py delete [id]")
        else:
            cmd_delete(int(sys.argv[2]))
    elif cmd == 'clear_drafts':
        cmd_clear_drafts()
    elif cmd == 'clear_history':
        cmd_clear_history()
    elif cmd == 'ai_stats':
        cmd_ai_stats()
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: storage, history, drafts, delete [id], clear_drafts, clear_history, ai_stats")
