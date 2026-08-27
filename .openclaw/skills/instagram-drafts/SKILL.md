# Instagram Drafts — Human-in-the-Loop Preview & Approval

**Skill:** `instagram-drafts`
**Description:** Staged post creation with approval workflow. Preview generates A/B variants + compliance score + alt-text. User approves/rejects via Telegram inline keyboard or CLI.
**Triggers:** "preview this", "draft this", safety mode always (destructive posts require approve)

## Commands

```bash
# Create preview
~/post-preview.sh "IMAGE_URL" "TONE" "DESCRIPTION"
python cli.py preview "URL" --tone casual --description "optional"

# Approve / Reject / Edit
~/post-approve.sh DRAFT_ID
python cli.py approve 47

~/post-reject.sh DRAFT_ID
python cli.py reject 47

python cli.py update 47 "New caption text"
python cli.py db drafts   # list pending
```

## Flow
`flowchart.md:168-190`
1. `VisionAgent.describe_image()` `agents/vision_agent.py:1`
2. `BrandService.get_active()` `services/brand_service.py:21`
3. `CreatorAgent.generate_caption_variants()` → `DraftService.create()` `services/draft_service.py:24` saves to `drafts` `db/setup_db.py:91` `status=PENDING`
4. Telegram `telegram/bot.py` renders card `SPEC_SHEET.md:858-864` 4 rows inline keyboards
5. `CallbackQuery approve:47` → `DraftService.approve()` `services/draft_service.py:113` → `PublisherAgent.publish()` → `posts.status=POSTED` `db/setup_db.py:58`, draft deleted

## Inline Keyboard (Telegram)
```
Row1: [✅ Approve & Post] [⏰ Schedule]
Row2: [✏️ Edit Caption] [🔄 Change Tone]
Row3: [🎨 Regenerate Image] [📱 Add Platform]
Row4: [❌ Discard]
Use A/B: [Use A] [Use B] selector when variants=2-3
```

## Verification
`python cli.py preview https://picsum.photos/200` → `DRAFT_ID` printed; `telegram` tap Approve → `posts` row.
