#!/usr/bin/env python3
"""
Shared Composio client helper — single source of truth for connecting
to Instagram via Composio.

Fixes a real bug hit in production: connected_accounts.list() can
return MULTIPLE connections for the same toolkit (e.g. an old EXPIRED
one left over from a previous OAuth session plus a new ACTIVE one after
reconnecting). Blindly taking items[0] assumes API ordering that isn't
guaranteed — this explicitly filters for status == 'ACTIVE' instead.

Usage:
    from pipelines.ig_connection import get_instagram_client

    client, user_id, connected_account_id, ig_user_id = get_instagram_client()
"""

import os


class NoActiveInstagramConnection(Exception):
    """Raised when no ACTIVE Instagram connection exists in Composio."""
    pass


def get_instagram_client():
    """
    Returns (client, user_id, connected_account_id, ig_user_id) for the
    ACTIVE Instagram connection. Raises NoActiveInstagramConnection with
    a clear, actionable message if none is found — instead of failing
    deep inside a tool call after an AI caption has already been
    generated and a draft already saved.
    """
    from composio import Composio

    api_key = os.getenv('COMPOSIO_API_KEY')
    if not api_key:
        raise NoActiveInstagramConnection(
            "COMPOSIO_API_KEY is not set in .env"
        )

    client = Composio(api_key=api_key)
    accounts = client.connected_accounts.list()
    items = dict(accounts).get('items', [])

    instagram_accounts = [
        acc for acc in items
        if 'instagram' in str(getattr(acc, 'toolkit', '')).lower()
    ]

    if not instagram_accounts:
        raise NoActiveInstagramConnection(
            "No Instagram account connected in Composio. "
            "Connect one at dashboard.composio.dev -> Connected Accounts."
        )

    active_accounts = [
        acc for acc in instagram_accounts
        if getattr(acc, 'status', None) == 'ACTIVE'
    ]

    if not active_accounts:
        statuses = ', '.join(
            f"{acc.id}={getattr(acc, 'status', 'unknown')}"
            for acc in instagram_accounts
        )
        raise NoActiveInstagramConnection(
            f"No ACTIVE Instagram connection found (found: {statuses}). "
            "Reconnect at dashboard.composio.dev -> Connected Accounts -> "
            "Instagram -> Reconnect."
        )

    if len(active_accounts) > 1:
        print(
            f"[WARNING] {len(active_accounts)} ACTIVE Instagram connections "
            f"found — using the first ({active_accounts[0].id}). "
            "Consider removing duplicates in the Composio dashboard."
        )

    account = active_accounts[0]
    user_id = account.user_id
    connected_account_id = account.id
    ig_user_id = os.getenv('INSTAGRAM_USER_ID')

    if not ig_user_id:
        raise NoActiveInstagramConnection(
            "INSTAGRAM_USER_ID is not set in .env"
        )

    return client, user_id, connected_account_id, ig_user_id
