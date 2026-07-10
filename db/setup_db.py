#!/usr/bin/env python3
"""
SQLite Database Setup
Creates all tables for uct-insta-agent.
Safe to run multiple times — uses CREATE TABLE IF NOT EXISTS.
Usage: python3 db/setup_db.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'uct_agent.sqlite')

def setup():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1 — Post history
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE,
            caption TEXT,
            media_type TEXT,
            tone TEXT,
            image_url TEXT,
            provider TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            reach INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            saved INTEGER DEFAULT 0
        )
    ''')

    # 2 — Drafts (preview flow)
    c.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_url TEXT,
            caption TEXT,
            tone TEXT,
            media_type TEXT,
            status TEXT DEFAULT "PENDING",
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3 — Analytics cache
    c.execute('''
        CREATE TABLE IF NOT EXISTS analytics_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT,
            summary TEXT,
            content_ranking TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4 — AI call log
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT,
            model TEXT,
            prompt_type TEXT,
            success INTEGER DEFAULT 1,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5 — AI rotation state
    c.execute('''
        CREATE TABLE IF NOT EXISTS ai_rotation (
            id INTEGER PRIMARY KEY DEFAULT 1,
            current_index INTEGER DEFAULT 0,
            last_provider TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert default rotation row if not exists
    c.execute('''
        INSERT OR IGNORE INTO ai_rotation (id, current_index)
        VALUES (1, 0)
    ''')

    conn.commit()
    conn.close()

    print(f"Database initialized: {DB_PATH}")
    print("Tables created: posts, drafts, analytics_cache, ai_calls, ai_rotation")

    # Show DB size
    size = os.path.getsize(DB_PATH)
    print(f"Database size: {size} bytes")

if __name__ == '__main__':
    setup()
