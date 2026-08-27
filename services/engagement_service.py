"""
Engagement Service: Direct Message & Comment Management with Sentiment Scoring
"""

import os
import requests
import logging
from typing import List, Dict, Any, Optional

from adapters.instagram import InstagramAdapter
from core.model_router import get_default_router
from db.repository import get_seen_dms, mark_dm_seen

logger = logging.getLogger("clawagent.engagement")

class EngagementService:
    def __init__(self):
        self.ig_adapter = InstagramAdapter()
        self.router = get_default_router()
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.notify_chat_id = os.getenv("TELEGRAM_NOTIFY_CHAT_ID")

    def send_telegram(self, message: str) -> bool:
        if not self.telegram_bot_token or not self.notify_chat_id:
            logger.info(f"[Telegram Notification]: {message}")
            return False
        
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        try:
            resp = requests.post(url, json={"chat_id": self.notify_chat_id, "text": message}, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to send Telegram message: {e}")
            return False

    def get_dms(self, limit: int = 10, notify: bool = False) -> List[Dict[str, Any]]:
        client, account_id, _ = self.ig_adapter.get_client()
        try:
            res = client.actions.execute(
                action="INSTAGRAM_GET_CONVERSATIONS",
                params={"limit": limit},
                connected_account_id=account_id
            )
            conversations = res.get("data", {}).get("data", [])
            seen_ids = set(get_seen_dms(platform="INSTAGRAM"))
            
            new_conversations = []
            for c in conversations:
                cid = c.get("id")
                if cid and cid not in seen_ids:
                    new_conversations.append(c)
                    mark_dm_seen(cid, platform="INSTAGRAM")
                    if notify:
                        self.send_telegram(f"📩 New Instagram DM from {c.get('sender', {}).get('username', 'user')}")

            return conversations
        except Exception as e:
            logger.error(f"Failed to fetch DMs: {e}")
            return []

    def classify_sentiment(self, comment_text: str) -> str:
        """Classifies comment sentiment as POSITIVE, NEUTRAL, or NEGATIVE."""
        try:
            res = self.router.generate_text(
                task_type="fast_formatting",
                prompt=f"Classify the sentiment of this comment as exactly POSITIVE, NEUTRAL, or NEGATIVE:\n\n'{comment_text}'",
                max_tokens=10,
                temperature=0.0
            )
            res_clean = res.strip().upper()
            if "POSITIVE" in res_clean:
                return "POSITIVE"
            elif "NEGATIVE" in res_clean:
                return "NEGATIVE"
            return "NEUTRAL"
        except Exception:
            return "NEUTRAL"
