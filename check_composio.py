#!/usr/bin/env python3
"""
Composio API key + Instagram connection health check.
Read-only — does NOT post anything to Instagram.
Usage: python3 check_composio.py
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

def mask(key):
    """Show only first 6 / last 4 chars so the log is safe to paste."""
    if not key:
        return "(not set)"
    if len(key) <= 12:
        return key[:3] + "..." + key[-2:]
    return key[:6] + "..." + key[-4:]

def main():
    composio_key = os.getenv('COMPOSIO_API_KEY')
    ig_user_id = os.getenv('INSTAGRAM_USER_ID')

    print("=" * 50)
    print("STEP 1 — Environment check")
    print("=" * 50)
    print(f"COMPOSIO_API_KEY:   {mask(composio_key)}")
    print(f"INSTAGRAM_USER_ID:  {ig_user_id or '(not set)'}")

    if not composio_key:
        print("\nFAILED: COMPOSIO_API_KEY is not set in .env")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("STEP 2 — Composio API key validity")
    print("=" * 50)
    try:
        from composio import Composio
        client = Composio(api_key=composio_key)
        accounts = client.connected_accounts.list()
        print("Composio API key is VALID — request succeeded.")
    except Exception as e:
        print(f"FAILED: Composio API key rejected or request errored.")
        print(f"Error: {e}")
        print("\nLikely cause: key is wrong, revoked, or expired.")
        print("Fix: regenerate at dashboard.composio.dev -> Settings -> API Keys")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("STEP 3 — Connected accounts")
    print("=" * 50)
    items = dict(accounts).get('items', [])
    if not items:
        print("No connected accounts found at all.")
        print("Fix: connect Instagram in the Composio dashboard first.")
        sys.exit(1)

    print(f"Found {len(items)} connected account(s):\n")

    instagram_accounts = []
    for acc in items:
        toolkit = getattr(acc, 'toolkit', None) or getattr(acc, 'app_name', 'unknown')
        status = getattr(acc, 'status', 'unknown')
        acc_id = getattr(acc, 'id', 'unknown')
        print(f"  - id: {acc_id}")
        print(f"    toolkit: {toolkit}")
        print(f"    status:  {status}")
        print()
        if 'instagram' in str(toolkit).lower():
            instagram_accounts.append(acc)

    print("=" * 50)
    print("STEP 4 — Instagram-specific check")
    print("=" * 50)
    if not instagram_accounts:
        print("No Instagram connection found among connected accounts.")
        print("Fix: connect Instagram in Composio dashboard.")
        sys.exit(1)

    ig = instagram_accounts[0]
    status = getattr(ig, 'status', 'unknown')
    print(f"Instagram connected_account_id: {ig.id}")
    print(f"Status: {status}")

    if status == 'ACTIVE':
        print("\nRESULT: Instagram connection is ACTIVE. Safe to post.")
    elif status == 'EXPIRED':
        print("\nRESULT: Instagram connection is EXPIRED.")
        print("Fix: Composio dashboard -> Connected Accounts -> Instagram -> Reconnect")
        print("(Expected after the recent account suspension/recovery — Meta")
        print(" typically invalidates the prior OAuth token on suspension,")
        print(" even after the account itself is reinstated.)")
    else:
        print(f"\nRESULT: Unexpected status '{status}' — check Composio dashboard for details.")

    print("\n" + "=" * 50)
    print("STEP 5 — INSTAGRAM_USER_ID sanity check")
    print("=" * 50)
    if not ig_user_id:
        print("INSTAGRAM_USER_ID is not set in .env — required even if connection is ACTIVE.")
    else:
        print(f"INSTAGRAM_USER_ID is set: {ig_user_id}")
        print("(This should be the numeric IG Business ID from INSTAGRAM_GET_USER_INFO —")
        print(" if the account was suspended/reinstated, confirm this ID is unchanged.)")

if __name__ == '__main__':
    main()
