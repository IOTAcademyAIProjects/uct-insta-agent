# Instagram Post — Single Image/Video Publishing

**Skill:** `instagram-post`
**Description:** Post a single photo or video to Instagram with AI-generated, brand-aware captions. Supports FEED, REEL, STORY via media_type.
**Triggers:** user sends image URL + "post this", "publish to Instagram", "post with caption"

## Commands

```bash
# Direct post (generates caption + publishes)
~/post-to-instagram.sh "IMAGE_URL" "TONE" "DESCRIPTION"
# e.g. ~/post-to-instagram.sh "https://example.com/photo.jpg" "casual" "artisan coffee beans flat-lay"

# Via CLI (same)
python cli.py post "IMAGE_URL" --tone casual --platforms INSTAGRAM --description "optional"
```

## Adapter Contract
- `PublisherAgent.publish(platforms=["INSTAGRAM"])` `agents/publisher_agent.py:33`
- `InstagramAdapter.publish()` `adapters/instagram.py:1` → Composio `INSTAGRAM_CREATE_MEDIA_CONTAINER` → `CREATE_POST`
- MediaSpec `adapters/base.py:9` 1:1/4:5, 2200 chars, 30 hashtags

## Security
- `validate_safe_url` `core/security.py:52` blocks SSRF/private IPs
- `sanitize_user_input` for tone/description
- Allowlist via `openclaw-config/openclaw.json:allowFrom`

## Fallback
If caption generation fails, uses vision description `agents/vision_agent.py:1` via `gemini_flash` → `model_router.py:185 describe_image`
