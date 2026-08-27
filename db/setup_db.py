#!/usr/bin/env python3
"""
Database Setup Script for ClawAgent v3.0 (SQLite)
Creates all 13 tables and automatically migrates missing columns on existing tables.
"""

import sys
import os
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

DB_PATH = os.getenv('DB_PATH', os.path.join(PROJECT_ROOT, 'db', 'uct_agent.sqlite'))

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS brands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        is_active BOOLEAN DEFAULT 0,
        color_palette TEXT DEFAULT '["#000000", "#FFFFFF"]',
        typography_style TEXT DEFAULT 'modern-sans',
        visual_mood TEXT DEFAULT 'clean, vibrant, authentic',
        logo_url TEXT,
        tone_of_voice TEXT DEFAULT 'casual and engaging',
        avg_sentence_length REAL DEFAULT 15.0,
        emoji_frequency REAL DEFAULT 2.0,
        emoji_style TEXT DEFAULT 'moderate',
        hashtag_count_range TEXT DEFAULT '5-7',
        prohibited_words TEXT DEFAULT '',
        mandatory_elements TEXT DEFAULT '',
        sample_hooks TEXT DEFAULT '[]',
        instagram_user_id TEXT,
        linkedin_urn TEXT,
        twitter_handle TEXT,
        youtube_channel_id TEXT,
        composio_account_id TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER REFERENCES brands(id),
        title TEXT,
        description TEXT,
        source_content TEXT,
        status TEXT DEFAULT 'DRAFT',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER REFERENCES campaigns(id),
        brand_id INTEGER REFERENCES brands(id),
        platform TEXT NOT NULL DEFAULT 'INSTAGRAM',
        post_type TEXT DEFAULT 'FEED',
        caption TEXT,
        alt_text TEXT,
        media_urls TEXT,
        media_format TEXT DEFAULT '1:1',
        caption_provider TEXT,
        vision_provider TEXT,
        image_gen_provider TEXT,
        brand_compliance_score REAL DEFAULT 1.0,
        post_id TEXT UNIQUE,
        media_type TEXT DEFAULT 'IMAGE',
        tone TEXT DEFAULT 'casual',
        image_url TEXT,
        provider TEXT,
        status TEXT DEFAULT 'POSTED',
        scheduled_time DATETIME,
        posted_at DATETIME,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        reach INTEGER DEFAULT 0,
        impressions INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        saved INTEGER DEFAULT 0,
        engagement_rate REAL DEFAULT 0.0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER REFERENCES brands(id),
        caption_variants TEXT,
        selected_variant INTEGER DEFAULT 0,
        image_url TEXT,
        caption TEXT,
        tone TEXT DEFAULT 'casual',
        platforms TEXT DEFAULT '["INSTAGRAM"]',
        media_type TEXT DEFAULT 'IMAGE',
        status TEXT DEFAULT 'PENDING',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS competitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER REFERENCES brands(id),
        platform TEXT NOT NULL,
        handle TEXT NOT NULL,
        follower_count INTEGER DEFAULT 0,
        avg_engagement_rate REAL DEFAULT 0.0,
        last_scraped_at DATETIME,
        UNIQUE(brand_id, platform, handle)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS competitor_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competitor_id INTEGER REFERENCES competitors(id),
        platform_post_id TEXT,
        post_type TEXT,
        caption_summary TEXT,
        estimated_engagement REAL DEFAULT 0.0,
        posted_at DATETIME,
        scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS trend_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER REFERENCES brands(id),
        topic TEXT NOT NULL,
        relevance_score REAL DEFAULT 0.5,
        source TEXT DEFAULT 'GOOGLE_TRENDS',
        trend_velocity TEXT DEFAULT 'RISING',
        suggested_content TEXT DEFAULT '[]',
        expires_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS content_ideas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER REFERENCES brands(id),
        week_number INTEGER,
        idea_text TEXT,
        draft_caption TEXT,
        suggested_media TEXT,
        target_platform TEXT DEFAULT 'INSTAGRAM',
        source_trend_id INTEGER REFERENCES trend_insights(id),
        status TEXT DEFAULT 'SUGGESTED',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_calls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        model TEXT,
        prompt_type TEXT,
        task_type TEXT,
        success INTEGER DEFAULT 1,
        latency_ms INTEGER DEFAULT 0,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        error_message TEXT,
        brand_id INTEGER REFERENCES brands(id),
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS circuit_breaker_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        event_type TEXT,
        failure_count INTEGER DEFAULT 0,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduled_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id TEXT,
        brand_id INTEGER REFERENCES brands(id),
        image_url TEXT,
        caption TEXT,
        tone TEXT DEFAULT 'casual',
        media_type TEXT DEFAULT 'IMAGE',
        post_type TEXT DEFAULT 'FEED',
        scheduled_time DATETIME,
        scheduled_time_utc DATETIME,
        user_timezone TEXT DEFAULT 'UTC',
        optimal_time_suggested BOOLEAN DEFAULT 0,
        status TEXT DEFAULT 'PENDING',
        retry_count INTEGER DEFAULT 0,
        last_error TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS seen_dms (
        conversation_id TEXT PRIMARY KEY,
        platform TEXT DEFAULT 'INSTAGRAM',
        brand_id INTEGER REFERENCES brands(id),
        seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER REFERENCES brands(id),
        period TEXT,
        summary TEXT,
        content_ranking TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS improvement_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_id INTEGER REFERENCES brands(id),
        week_number INTEGER,
        experiment_type TEXT DEFAULT 'L1_HOOK',
        hypothesis TEXT,
        changed_field TEXT,
        old_value TEXT,
        new_value TEXT,
        metric_before REAL,
        metric_after REAL,
        predicted_lift REAL DEFAULT 0.0,
        status TEXT DEFAULT 'PROPOSED',
        dry_run BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        applied_at DATETIME,
        measured_at DATETIME
    );
    """
]

REQUIRED_COLUMNS = {
    "posts": [
        ("brand_id", "INTEGER DEFAULT 1"),
        ("platform", "TEXT DEFAULT 'INSTAGRAM'"),
        ("post_type", "TEXT DEFAULT 'FEED'"),
        ("campaign_id", "INTEGER"),
        ("alt_text", "TEXT"),
        ("media_urls", "TEXT"),
        ("media_format", "TEXT DEFAULT '1:1'"),
        ("caption_provider", "TEXT"),
        ("vision_provider", "TEXT"),
        ("image_gen_provider", "TEXT"),
        ("brand_compliance_score", "REAL DEFAULT 1.0"),
        ("status", "TEXT DEFAULT 'POSTED'"),
        ("scheduled_time", "DATETIME"),
        ("posted_at", "DATETIME"),
        ("impressions", "INTEGER DEFAULT 0"),
        ("shares", "INTEGER DEFAULT 0"),
        ("engagement_rate", "REAL DEFAULT 0.0"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    ],
    "drafts": [
        ("brand_id", "INTEGER DEFAULT 1"),
        ("caption_variants", "TEXT"),
        ("selected_variant", "INTEGER DEFAULT 0"),
        ("platforms", "TEXT DEFAULT '[\"INSTAGRAM\"]'")
    ],
    "ai_calls": [
        ("task_type", "TEXT"),
        ("latency_ms", "INTEGER DEFAULT 0"),
        ("input_tokens", "INTEGER DEFAULT 0"),
        ("output_tokens", "INTEGER DEFAULT 0"),
        ("error_message", "TEXT"),
        ("brand_id", "INTEGER DEFAULT 1")
    ],
    "scheduled_posts": [
        ("brand_id", "INTEGER DEFAULT 1"),
        ("scheduled_time_utc", "DATETIME"),
        ("user_timezone", "TEXT DEFAULT 'UTC'"),
        ("optimal_time_suggested", "BOOLEAN DEFAULT 0"),
        ("retry_count", "INTEGER DEFAULT 0"),
        ("last_error", "TEXT")
    ]
}

def migrate_missing_columns(cursor):
    """Dynamically adds missing columns to existing SQLite tables."""
    for table, columns in REQUIRED_COLUMNS.items():
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            existing_cols = {row[1] for row in cursor.fetchall()}
            for col_name, col_def in columns:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass

def setup_database():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=15000;")
        cursor.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        pass

    for ddl in DDL_STATEMENTS:
        cursor.execute(ddl)

    migrate_missing_columns(cursor)

    cursor.execute("SELECT COUNT(*) FROM brands")
    count = cursor.fetchone()[0]
    if count == 0:
        default_brand_name = os.getenv("BRAND_NAME", "DefaultBrand")
        cursor.execute(
            """INSERT INTO brands (name, is_active, tone_of_voice, color_palette, emoji_frequency, hashtag_count_range)
               VALUES (?, 1, 'casual, authentic and engaging', '["#000000", "#FFFFFF"]', 2.0, '5-7')""",
            (default_brand_name,)
        )

    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_database()
    print("Database setup & column migration completed successfully.")
