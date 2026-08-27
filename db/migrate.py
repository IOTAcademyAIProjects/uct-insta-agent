#!/usr/bin/env python3
"""
Database Migration Utility: Upgrades schemas and preserves historical data.
"""

import sys
import os
import sqlite3
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from db.repository import get_db_path
from db.setup_db import setup_database

def migrate_database():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print("No existing database file found. Running initial setup...")
        setup_database()
        return

    print(f"Checking migration requirements for {db_path}...")
    setup_database()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure all existing posts have brand_id and platform
    cursor.execute("UPDATE posts SET brand_id = 1 WHERE brand_id IS NULL")
    cursor.execute("UPDATE posts SET platform = 'INSTAGRAM' WHERE platform IS NULL")
    cursor.execute("UPDATE drafts SET brand_id = 1 WHERE brand_id IS NULL")
    cursor.execute("UPDATE ai_calls SET brand_id = 1 WHERE brand_id IS NULL")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == '__main__':
    migrate_database()
