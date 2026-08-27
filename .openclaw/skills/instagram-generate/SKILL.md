# Instagram Generate — AI Visual via Pollinations (Flux)

**Skill:** `instagram-generate`
**Description:** Generate an AI visual from text prompt via Pollinations AI (Flux) and create a preview draft. Free, no API key needed for pollinations default.
**Triggers:** "generate an image of...", "create an AI visual", "imagine ..."

## Commands

```bash
~/generate-image.sh "PROMPT" "TONE"
# e.g. ~/generate-image.sh "futuristic city in cyber aesthetic" "casual"

python cli.py generate "futuristic city" --tone inspirational
```

## Pipeline
`agents/designer_agent.py:1` `Designers generate_image()` → `core/model_router.py:224 generate_image()` `fallback_chains.image_generation=[pollinations, banana_dev, replicate]` `config/models.yaml:153`
→ `DraftService.create(image_url, tone, description=prompt)` `services/draft_service.py:24`

## Security
`sanitize_user_input(prompt, max_length=1000)` `cli.py:111`
Provider cost_tier free `config/models.yaml:92`

## Verification
`python cli.py generate "minimalist coffee logo"` → `IMAGE_URL` + `DRAFT_ID` preview
