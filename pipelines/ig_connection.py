#!/usr/bin/env python3
"""
Instagram Connection Helper — Backward-Compatible Wrapper for ClawAgent v3.0
Delegates to adapters.instagram.InstagramAdapter.
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from adapters.instagram import InstagramAdapter
from core.exceptions import NoActiveInstagramConnection

_adapter = InstagramAdapter()

def get_instagram_client():
    """Returns verified active Composio Instagram client, account_id, and ig_user_id."""
    return _adapter.get_client()

if __name__ == '__main__':
    try:
        client, account_id, ig_user_id = get_instagram_client()
        print(f"Instagram Connection Active:")
        print(f"  Account ID: {account_id}")
        print(f"  IG User ID: {ig_user_id}")
    except NoActiveInstagramConnection as e:
        print(f"Error: {e}")
        sys.exit(1)
