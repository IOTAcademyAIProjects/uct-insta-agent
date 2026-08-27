"""
Telegram Inline Keyboard Builders — SPEC_SHEET.md:858-876
Pure logic, no Telegram SDK dependency for unit testing.
Returns dict structures convertible to InlineKeyboardMarkup.
"""

from typing import List, Dict, Any

def build_draft_keyboard(draft_id: int, has_variants: bool = True, platforms: List[str] = None) -> List[List[Dict[str, str]]]:
    """
    Draft preview card 4-row layout SPEC_SHEET.md:858-864
    Row1: Approve & Post | Schedule
    Row2: Edit Caption | Change Tone
    Row3: Regenerate Image | Add Platform
    Row4: Discard
    Optional Use A/B row if variants
    """
    kb = [
        [
            {"text": "✅ Approve & Post", "callback_data": f"approve:{draft_id}"},
            {"text": "⏰ Schedule", "callback_data": f"schedule:{draft_id}"}
        ],
        [
            {"text": "✏️ Edit Caption", "callback_data": f"edit:{draft_id}"},
            {"text": "🔄 Change Tone", "callback_data": f"tone:{draft_id}"}
        ],
        [
            {"text": "🎨 Regenerate Image", "callback_data": f"regen:{draft_id}"},
            {"text": "📱 Add Platform", "callback_data": f"platform:{draft_id}"}
        ],
        [
            {"text": "❌ Discard", "callback_data": f"discard:{draft_id}"}
        ],
    ]
    if has_variants:
        kb.insert(1, [
            {"text": "🅰️ Use A", "callback_data": f"use_a:{draft_id}"},
            {"text": "🅱️ Use B", "callback_data": f"use_b:{draft_id}"}
        ])
    return kb

def build_brand_keyboard(brands: List[Dict[str, Any]], active_name: str = None) -> List[List[Dict[str, str]]]:
    """Brand switcher SPEC_SHEET.md:868-871"""
    rows = []
    current = []
    for b in brands:
        name = b.get("name","Brand")
        label = f"🏷️ {name}" + (" (active)" if name == active_name else "")
        current.append({"text": label, "callback_data": f"brand_switch:{name}"})
        if len(current) == 2:
            rows.append(current)
            current = []
    if current:
        rows.append(current)
    rows.append([{"text": "➕ New Brand", "callback_data": "brand_new"}])
    return rows

def build_analytics_keyboard() -> List[List[Dict[str, str]]]:
    """Analytics quick actions SPEC_SHEET.md:872-876"""
    return [
        [
            {"text": "📊 Last 7 Days", "callback_data": "analytics:7"},
            {"text": "📊 Last 30 Days", "callback_data": "analytics:30"}
        ],
        [
            {"text": "📊 Custom Range", "callback_data": "analytics:custom"},
            {"text": "🔍 Competitor Compare", "callback_data": "analytics:competitor"}
        ]
    ]

def build_self_improve_keyboard(proposal_id: int) -> List[List[Dict[str, str]]]:
    """Self-Improving Loop HITL card — PRD 3.13, SPEC 9"""
    return [
        [
            {"text": "✅ Apply Insight", "callback_data": f"improve_apply:{proposal_id}"},
            {"text": "❌ Reject", "callback_data": f"improve_reject:{proposal_id}"}
        ],
        [
            {"text": "📊 View Details", "callback_data": f"improve_view:{proposal_id}"},
            {"text": "📈 History", "callback_data": f"improve_history:1"}
        ],
    ]

def render_self_improve_text(proposal: Dict[str, Any], brand_name: str = "Brand") -> str:
    """Renders self-improvement proposal card for Telegram."""
    field = proposal.get("changed_field","unknown")
    old = proposal.get("old_value","")[:60]
    new = proposal.get("new_value","")[:60]
    hyp = proposal.get("hypothesis","")[:300]
    lift = proposal.get("predicted_lift",0)
    status = proposal.get("status","PROPOSED")
    exp_type = proposal.get("experiment_type","L1")
    before = proposal.get("metric_before",0)
    return (
        f"🧬 Self-Improvement Proposal #{proposal.get('id')} — {brand_name} | {status}\n\n"
        f"Type: {exp_type} | Field: `{field}`\n"
        f"From: `{old}`\n→ To: `{new}`\n\n"
        f"Hypothesis: {hyp}\n\n"
        f"Predicted lift: {lift:.0%} | Baseline eng: {before:.2f}%\n"
        f"Week: {proposal.get('week_number')} | Dry-run: {bool(proposal.get('dry_run'))}\n\n"
        f"Approve to apply to Brand Profile. Measure after 7d auto-keep/revert."
    )

def to_telegram_markup(keyboard: List[List[Dict[str, str]]]):
    """Converts dict keyboard to python-telegram-bot InlineKeyboardMarkup if available."""
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        tg_kb = []
        for row in keyboard:
            tg_row = [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]) for btn in row]
            tg_kb.append(tg_row)
        return InlineKeyboardMarkup(tg_kb)
    except ImportError:
        # Return raw dict for testing without SDK
        return keyboard

def render_draft_preview_text(draft: Dict[str, Any], brand_name: str = "Brand", compliance: Dict[str, Any] = None) -> str:
    """Renders draft preview card markdown PRD.md:372-381"""
    caption = draft.get("caption","")[:300]
    variants = draft.get("caption_variants") or []
    if isinstance(variants, str):
        try:
            import json
            variants = json.loads(variants)
        except Exception:
            variants = [variants]
    tone = draft.get("tone","casual")
    platforms = draft.get("platforms","INSTAGRAM")
    if isinstance(platforms, str):
        try:
            import json
            platforms = ", ".join(json.loads(platforms))
        except Exception:
            pass
    alt_text = draft.get("alt_text") or "Auto alt-text will be generated"
    compliance_line = ""
    if compliance:
        score = compliance.get("score", 1.0)
        issues = compliance.get("issues", [])
        compliance_line = f"\nCompliance: {score:.0%} {'✅' if not issues else '⚠️ ' + '; '.join(issues[:2])}"

    md = (
        f"🖼️ Draft Preview #{draft.get('id')} — {brand_name}\n\n"
        f"Caption: {caption}\n"
    )
    if len(variants) > 1:
        md += f"\nVariant B: {variants[1][:150]}...\n"
    md += (
        f"\nPlatform: {platforms} | Tone: {tone.capitalize()}{compliance_line}\n"
        f"Alt-text: {alt_text[:100]}\n"
        f"Image: {draft.get('image_url','')[:60]}...\n"
    )
    return md
