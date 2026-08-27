# Instagram Carousel — Swipeable Album (2–10 images)

**Skill:** `instagram-carousel`
**Description:** Post multiple images as a single swipeable Instagram carousel album with AI carousel caption.
**Triggers:** user provides 2-10 URLs + "carousel", "album", "swipe"

## Commands

```bash
~/post-carousel.sh "URL1,URL2,URL3" "TONE"
# e.g. ~/post-carousel.sh "https://a.jpg,https://b.jpg,https://c.jpg" "casual"

python cli.py carousel "URL1,URL2" --tone inspirational
```

## Adapter
- Validates `len(urls) >=2` `cli.py:84-87`
- `PublisherAgent.publish(media_type="CAROUSEL")` `agents/publisher_agent.py:33`
- `InstagramAdapter` detects CAROUSEL → 1:1/4:5, 2-10 items `adapters/base.py:9`

## Security
- Each URL via `validate_safe_url` `core/security.py:52`
- Comma-split sanitized `cli.py:84`
