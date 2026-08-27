"""
Instagram Platform Adapter via Composio MCP & Meta Graph API
Hardened with Strict Response & Error Validation.
"""

import os
import time
import requests
import logging
from core.security import mask_secrets
from typing import List, Optional, Dict, Any, Tuple

from adapters.base import PlatformAdapter, MediaSpec, PublishResult
from core.exceptions import NoActiveInstagramConnection
from db.repository import log_post

logger = logging.getLogger("clawagent.instagram")

class InstagramAdapter(PlatformAdapter):
    def __init__(self, name: str = "instagram", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        self.api_key = os.getenv("COMPOSIO_API_KEY")
        self.account_id = os.getenv("COMPOSIO_ACCOUNT_ID")
        self.ig_user_id = os.getenv("INSTAGRAM_USER_ID")
        self._client = None

    def get_client(self):
        if not self.api_key:
            raise NoActiveInstagramConnection("COMPOSIO_API_KEY environment variable is not set.")

        if self._client is not None:
            return self._client, self.account_id, self.ig_user_id

        from composio import Composio
        client = Composio(api_key=self.api_key)

        account_id = self.account_id
        if not account_id:
            connected = client.connected_accounts.get()
            active_ig = [
                acc for acc in getattr(connected, "items", [])
                if getattr(acc, "appUniqueId", None) == "instagram"
                and getattr(acc, "status", None) == "ACTIVE"
            ]
            if not active_ig:
                raise NoActiveInstagramConnection("No ACTIVE Instagram connection found in Composio.")
            account_id = active_ig[0].id

        # Wrap client to support both legacy .tools (slug/arguments) and new .actions (action/params) for backward compat C-10
        client = self._wrap_composio_client(client)
        self._client = client
        self.account_id = account_id
        return self._client, self.account_id, self.ig_user_id

    def _wrap_composio_client(self, client):
        """Adds .tools alias to .actions and vice versa with param translation for legacy pipelines."""
        try:
            # If client has actions, make tools an alias that translates slug->action, arguments->params
            if hasattr(client, "actions") and not hasattr(client, "tools"):
                class _ToolsProxy:
                    def __init__(self, actions):
                        self._actions = actions
                    def execute(self, slug=None, action=None, arguments=None, params=None, **kwargs):
                        act = action or slug
                        pr = params if params is not None else arguments
                        return self._actions.execute(action=act, params=pr, **kwargs)
                client.tools = _ToolsProxy(client.actions)
            if hasattr(client, "tools") and not hasattr(client, "actions"):
                class _ActionsProxy:
                    def __init__(self, tools):
                        self._tools = tools
                    def execute(self, action=None, slug=None, params=None, arguments=None, **kwargs):
                        sl = slug or action
                        args = arguments if arguments is not None else params
                        return self._tools.execute(slug=sl, arguments=args, **kwargs)
                client.actions = _ActionsProxy(client.tools)
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")
        return client

    def _poll_container_ready(self, client, account_id, creation_id, timeout: int = 30):
        """Polls container status with exponential backoff instead of fixed sleep C-12."""
        # Try to use dedicated status check if available, otherwise just wait with backoff
        elapsed = 0
        delay = 2
        while elapsed < timeout:
            try:
                # Attempt status check via composio if action exists; ignore failure and just wait
                if hasattr(client, "actions"):
                    try:
                        # Some composio versions expose INSTAGRAM_GET_MEDIA_CONTAINER
                        res = client.actions.execute(
                            action="INSTAGRAM_GET_MEDIA",
                            params={"media_id": creation_id},
                            connected_account_id=account_id
                        )
                        data = res.get("data", {}) if isinstance(res, dict) else {}
                        status = str(data.get("status_code") or data.get("status") or "").upper()
                        if status in ("FINISHED", "READY"):
                            return True
                        if status in ("ERROR", "EXPIRED", "FAILED"):
                            logger.warning(f"Container {creation_id} status {status}")
                            return False
                    except Exception as e:
                            logger.warning(f"Handled Exception: {mask_secrets(str(e))}")  # Action not available, fall back to timed wait
                time.sleep(delay)
                elapsed += delay
                delay = min(delay * 1.5, 8)
                # For fast path (image), return after first poll if no status API
                if elapsed >= 6 and "CAROUSEL" not in str(creation_id):
                    return True
            except Exception:
                time.sleep(delay)
                elapsed += delay
        return True  # Proceed to publish after timeout

    def get_media_spec(self, post_type: str = "FEED") -> MediaSpec:
        if post_type.upper() == "STORY":
            return MediaSpec(
                aspect_ratios=["9:16"],
                max_file_size_mb=4.0,
                max_caption_length=0,
                max_hashtags=0
            )
        elif post_type.upper() == "REEL":
            return MediaSpec(
                aspect_ratios=["9:16"],
                max_file_size_mb=100.0,
                supported_formats=["mp4"],
                max_caption_length=2200,
                max_hashtags=30
            )
        else:
            return MediaSpec(
                aspect_ratios=["1:1", "4:5"],
                max_file_size_mb=8.0,
                supported_formats=["jpg", "jpeg", "png"],
                max_caption_length=2200,
                max_hashtags=30,
                max_carousel_items=10
            )

    def format_caption(self, raw_caption: str, brand_context: Optional[Dict[str, Any]] = None) -> str:
        return raw_caption[:2200]

    def _validate_action_response(self, res: Any, action_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates Composio/Meta API action responses against errors and extracts ID.
        Returns: (success: bool, id_or_none, error_message_or_none)
        """
        if not res or not isinstance(res, dict):
            return False, None, f"{action_name} returned invalid or empty response."

        # Check top-level error structures
        if res.get("successful") is False:
            err = res.get("error") or res.get("message") or "Action marked as unsuccessful"
            return False, None, str(err)

        if "error" in res:
            err_data = res["error"]
            err_msg = err_data.get("message") if isinstance(err_data, dict) else str(err_data)
            return False, None, f"Meta API Error: {err_msg}"

        data = res.get("data", {})
        if isinstance(data, dict):
            if "error" in data:
                return False, None, f"Meta API Error in data: {data['error']}"
            extracted_id = data.get("id") or data.get("creation_id") or data.get("post_id")
            if extracted_id:
                return True, str(extracted_id), None

        top_id = res.get("id") or res.get("creation_id")
        if top_id:
            return True, str(top_id), None

        return False, None, f"No valid ID returned in {action_name} response."

    def publish(
        self,
        media_urls: List[str],
        caption: str,
        media_type: str = "IMAGE",
        post_type: str = "FEED",
        brand_id: Optional[int] = None
    ) -> PublishResult:
        try:
            client, account_id, ig_user_id = self.get_client()
        except Exception as e:
            return PublishResult(platform="INSTAGRAM", success=False, error=str(e))

        if post_type.upper() == "STORY":
            return self._publish_story(client, account_id, ig_user_id, media_urls[0], caption, brand_id)
        elif len(media_urls) > 1:
            return self._publish_carousel(client, account_id, ig_user_id, media_urls, caption, brand_id)
        else:
            return self._publish_single(client, account_id, ig_user_id, media_urls[0], caption, media_type, brand_id)

    def _publish_single(self, client, account_id, ig_user_id, media_url, caption, media_type, brand_id) -> PublishResult:
        try:
            container_params = {"caption": caption}
            if ig_user_id:
                container_params["ig_user_id"] = ig_user_id

            if media_type.upper() in ("VIDEO", "REELS", "REEL"):
                container_params["video_url"] = media_url
                container_params["media_type"] = "REELS"
            else:
                container_params["image_url"] = media_url

            container_res = client.actions.execute(
                action="INSTAGRAM_CREATE_MEDIA_CONTAINER",
                params=container_params,
                connected_account_id=account_id
            )
            
            c_ok, creation_id, c_err = self._validate_action_response(container_res, "CREATE_MEDIA_CONTAINER")
            if not c_ok or not creation_id:
                return PublishResult(
                    platform="INSTAGRAM",
                    success=False,
                    error=f"Failed to create media container: {c_err}",
                    raw_response=container_res
                )

            self._poll_container_ready(client, account_id, creation_id, timeout=30)
            publish_params = {"creation_id": creation_id}
            if ig_user_id:
                publish_params["ig_user_id"] = ig_user_id

            pub_res = client.actions.execute(
                action="INSTAGRAM_CREATE_POST",
                params=publish_params,
                connected_account_id=account_id
            )

            p_ok, post_id, p_err = self._validate_action_response(pub_res, "CREATE_POST")
            if not p_ok or not post_id:
                return PublishResult(
                    platform="INSTAGRAM",
                    success=False,
                    error=f"Failed to publish container {creation_id}: {p_err}",
                    raw_response=pub_res
                )

            log_post(
                post_id=str(post_id),
                caption=caption,
                media_type=media_type,
                tone="casual",
                image_url=media_url,
                provider="Composio",
                brand_id=brand_id,
                platform="INSTAGRAM"
            )

            return PublishResult(
                platform="INSTAGRAM",
                success=True,
                post_id=str(post_id),
                permalink=f"https://instagram.com/p/{post_id}",
                raw_response=pub_res
            )
        except Exception as e:
            logger.error(f"Instagram publish single failed: {e}")
            return PublishResult(platform="INSTAGRAM", success=False, error=str(e))

    def _publish_carousel(self, client, account_id, ig_user_id, media_urls, caption, brand_id) -> PublishResult:
        try:
            children_ids = []
            for url in media_urls[:10]:
                child_params = {
                    "image_url": url,
                    "is_carousel_item": True
                }
                if ig_user_id:
                    child_params["ig_user_id"] = ig_user_id

                c_res = client.actions.execute(
                    action="INSTAGRAM_CREATE_MEDIA_CONTAINER",
                    params=child_params,
                    connected_account_id=account_id
                )
                c_ok, cid, _ = self._validate_action_response(c_res, "CREATE_CAROUSEL_ITEM")
                if c_ok and cid:
                    children_ids.append(cid)
                    self._poll_container_ready(client, account_id, cid, timeout=15)

            if len(children_ids) < 2:
                return PublishResult(platform="INSTAGRAM", success=False, error="Carousel requires at least 2 valid image containers.")

            carousel_params = {
                "media_type": "CAROUSEL",
                "caption": caption,
                "children": children_ids
            }
            if ig_user_id:
                carousel_params["ig_user_id"] = ig_user_id

            root_res = client.actions.execute(
                action="INSTAGRAM_CREATE_MEDIA_CONTAINER",
                params=carousel_params,
                connected_account_id=account_id
            )
            r_ok, creation_id, r_err = self._validate_action_response(root_res, "CREATE_CAROUSEL_ROOT")
            if not r_ok or not creation_id:
                return PublishResult(platform="INSTAGRAM", success=False, error=f"Failed to create carousel root container: {r_err}")

            self._poll_container_ready(client, account_id, creation_id, timeout=30)
            publish_params = {"creation_id": creation_id}
            if ig_user_id:
                publish_params["ig_user_id"] = ig_user_id

            pub_res = client.actions.execute(
                action="INSTAGRAM_CREATE_POST",
                params=publish_params,
                connected_account_id=account_id
            )
            p_ok, post_id, p_err = self._validate_action_response(pub_res, "PUBLISH_CAROUSEL")
            if not p_ok or not post_id:
                return PublishResult(platform="INSTAGRAM", success=False, error=f"Failed to publish carousel: {p_err}")

            log_post(
                post_id=str(post_id),
                caption=caption,
                media_type="CAROUSEL",
                tone="casual",
                image_url=media_urls[0],
                provider="Composio",
                brand_id=brand_id,
                platform="INSTAGRAM"
            )

            return PublishResult(
                platform="INSTAGRAM",
                success=True,
                post_id=str(post_id),
                permalink=f"https://instagram.com/p/{post_id}",
                raw_response=pub_res
            )
        except Exception as e:
            logger.error(f"Instagram carousel publish failed: {e}")
            return PublishResult(platform="INSTAGRAM", success=False, error=str(e))

    def _publish_story(self, client, account_id, ig_user_id, media_url, caption, brand_id) -> PublishResult:
        try:
            story_params = {
                "image_url": media_url,
                "media_type": "STORIES"
            }
            if ig_user_id:
                story_params["ig_user_id"] = ig_user_id

            container_res = client.actions.execute(
                action="INSTAGRAM_CREATE_MEDIA_CONTAINER",
                params=story_params,
                connected_account_id=account_id
            )
            c_ok, creation_id, c_err = self._validate_action_response(container_res, "CREATE_STORY_CONTAINER")
            if not c_ok or not creation_id:
                return PublishResult(platform="INSTAGRAM", success=False, error=f"Failed to create story container: {c_err}")

            self._poll_container_ready(client, account_id, creation_id, timeout=30)
            pub_params = {"creation_id": creation_id}
            if ig_user_id:
                pub_params["ig_user_id"] = ig_user_id

            pub_res = client.actions.execute(
                action="INSTAGRAM_CREATE_POST",
                params=pub_params,
                connected_account_id=account_id
            )
            p_ok, post_id, p_err = self._validate_action_response(pub_res, "PUBLISH_STORY")
            if not p_ok or not post_id:
                return PublishResult(platform="INSTAGRAM", success=False, error=f"Failed to publish story: {p_err}")

            return PublishResult(
                platform="INSTAGRAM",
                success=True,
                post_id=str(post_id),
                raw_response=pub_res
            )
        except Exception as e:
            return PublishResult(platform="INSTAGRAM", success=False, error=str(e))

    def get_analytics(self, date_range: tuple, limit: int = 50) -> Dict[str, Any]:
        client, account_id, ig_user_id = self.get_client()
        params = {"limit": limit}
        if ig_user_id:
            params["ig_user_id"] = ig_user_id

        res = client.actions.execute(
            action="INSTAGRAM_GET_USER_MEDIA",
            params=params,
            connected_account_id=account_id
        )
        return res
