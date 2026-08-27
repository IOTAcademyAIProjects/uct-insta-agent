"""
Telegram Callback Router — maps callback_data to services
Design: single entry handle_callback(data, user_id) for testability
"""

import logging
from typing import Dict, Any

from services.draft_service import DraftService
from services.brand_service import BrandService
from services.scheduler_service import SchedulerService
from agents.publisher_agent import PublisherAgent
from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent
from telegram.keyboards import build_draft_keyboard, build_brand_keyboard, build_analytics_keyboard, build_self_improve_keyboard
from core.security import sanitize_user_input, SecurityException

logger = logging.getLogger("clawagent.telegram.callbacks")

def handle_callback(callback_data: str, user_id: str = None) -> Dict[str, Any]:
    """
    Routes callback_data like 'approve:47', 'brand_switch:BrandX', 'analytics:7'.
    Returns dict {text, keyboard, action} for bot to answer.
    Allowlist should be checked by caller before invoking.
    """
    if not callback_data or ":" not in callback_data and "_" not in callback_data:
        # Handle simple callbacks like brand_new
        if callback_data == "brand_new":
            return {"text": "Send: /brand create <name> --tone <tone>", "keyboard": None}
        return {"text": "Unknown action", "keyboard": None}

    # Parse action:id or action:value
    if ":" in callback_data:
        action, value = callback_data.split(":", 1)
        value = sanitize_user_input(value, max_length=100)
    else:
        action, value = callback_data, ""

    try:
        if action == "approve":
            draft_id = int(value)
            ds = DraftService()
            # Check variant selection if user previously chose A/B? default 0
            res = ds.approve(draft_id)
            if res.get("success"):
                results = res.get("results", {})
                lines = []
                for plat, r in results.items():
                    if getattr(r, 'success', False):
                        lines.append(f"✅ {plat}: {getattr(r,'post_id','posted')}")
                    else:
                        lines.append(f"❌ {plat}: {getattr(r,'error','failed')}")
                return {"text": f"✅ Draft {draft_id} posted!\n" + "\n".join(lines), "keyboard": None, "action": "posted"}
            return {"text": f"❌ Failed to approve {draft_id}: {res.get('error')}", "keyboard": None}

        elif action in ("use_a", "use_b"):
            draft_id = int(value)
            variant_idx = 0 if action == "use_a" else 1
            from db.repository import get_draft
            draft = get_draft(draft_id)
            if not draft:
                return {"text": f"Draft {draft_id} not found", "keyboard": None}
            # Update selected_variant in DB
            try:
                from db.repository import get_connection
                conn = get_connection()
                conn.execute("UPDATE drafts SET selected_variant=? WHERE id=?", (variant_idx, draft_id))
                conn.commit()
                conn.close()
                # Also update caption to chosen variant for preview
                import json
                vars_raw = draft.get("caption_variants") or "[]"
                variants = json.loads(vars_raw) if isinstance(vars_raw, str) else vars_raw
                if variant_idx < len(variants):
                    from db.repository import update_draft_caption
                    update_draft_caption(draft_id, variants[variant_idx])
                return {"text": f"Selected Variant {'A' if variant_idx==0 else 'B'} for draft {draft_id}. Now tap Approve.", "keyboard": build_draft_keyboard(draft_id, has_variants=True), "action": "variant_selected"}
            except Exception as e:
                return {"text": f"Variant select failed: {e}", "keyboard": None}

        elif action == "discard":
            draft_id = int(value)
            ds = DraftService()
            if ds.reject(draft_id):
                return {"text": f"🗑️ Draft {draft_id} discarded.", "keyboard": None}
            return {"text": f"Draft {draft_id} not found", "keyboard": None}

        elif action == "schedule":
            return {"text": f"Send: /schedule {value} YYYY-MM-DD HH:MM (e.g. 2026-08-28 15:00)", "keyboard": None}

        elif action == "edit":
            return {"text": f"Reply with new caption for draft {value}:\n`python cli.py update {value} \"New caption\"`", "keyboard": None}

        elif action == "tone":
            return {"text": f"Send new tone for draft {value}: casual | inspirational | professional | witty", "keyboard": None}

        elif action == "regen":
            return {"text": f"Regenerating image for draft {value}... (uses DesignerAgent)", "keyboard": None}

        elif action == "platform":
            return {"text": f"Add platform for draft {value}: INSTAGRAM | LINKEDIN | TWITTER | YOUTUBE\nUse `python cli.py preview <url> --platforms INSTAGRAM,LINKEDIN`", "keyboard": None}

        elif action == "brand_switch":
            bs = BrandService()
            if bs.switch_brand(value):
                return {"text": f"✅ Active brand switched to '{value}'", "keyboard": None, "action": "brand_switched"}
            return {"text": f"❌ Brand '{value}' not found", "keyboard": None}

        elif action == "analytics":
            days = int(value) if value.isdigit() else 7
            try:
                analyst = AnalystAgent()
                res = analyst.analyze_performance(days=days)
                return {"text": f"📊 Performance ({res.get('date_range')}):\n{res.get('summary','No data')[:800]}", "keyboard": build_analytics_keyboard()}
            except Exception as e:
                return {"text": f"Analytics failed: {e}", "keyboard": None}

        elif action == "improve_apply":
            pid = int(value)
            from services.self_improvement_service import SelfImprovementService
            svc = SelfImprovementService()
            res = svc.approve(pid)
            if res.get("success"):
                p = res["proposal"]
                return {"text": f"✅ Applied #{pid}: {p['changed_field']} {p['old_value']} → {p['new_value']} | Measure in 7d auto-keep/revert.", "keyboard": None, "action": "improve_applied"}
            return {"text": f"❌ Apply failed: {res.get('error')}", "keyboard": build_self_improve_keyboard(pid)}

        elif action == "improve_reject":
            pid = int(value)
            from services.self_improvement_service import SelfImprovementService
            svc = SelfImprovementService()
            res = svc.reject(pid)
            if res.get("success"):
                return {"text": f"🗑️ Proposal #{pid} rejected.", "keyboard": None}
            return {"text": f"❌ Reject failed: {res.get('error')}", "keyboard": None}

        elif action == "improve_view":
            pid = int(value)
            from services.self_improvement_service import SelfImprovementService
            from db.repository import get_connection
            conn = get_connection()
            row = conn.execute("SELECT * FROM improvement_log WHERE id=?", (pid,)).fetchone()
            conn.close()
            if not row:
                return {"text": f"Proposal #{pid} not found", "keyboard": None}
            from telegram.keyboards import render_self_improve_text
            txt = render_self_improve_text(dict(row))
            return {"text": txt, "keyboard": build_self_improve_keyboard(pid)}

        elif action == "improve_history":
            from services.self_improvement_service import SelfImprovementService
            svc = SelfImprovementService()
            hist = svc.get_history(limit=5)
            if not hist:
                return {"text": "No improvement history yet. Run /improve propose", "keyboard": None}
            lines = "\n".join([f"#{h['id']} {h['changed_field']} {h['old_value']}→{h['new_value']} {h['status']} lift {h.get('predicted_lift',0):.0%}" for h in hist])
            return {"text": f"📈 Last 5 improvements:\n{lines}", "keyboard": None}

        else:
            return {"text": f"Unknown action: {action}", "keyboard": None}

    except ValueError as ve:
        return {"text": f"Invalid ID: {value}", "keyboard": None}
    except Exception as e:
        logger.error(f"Callback error {callback_data}: {e}")
        return {"text": f"Error: {e}", "keyboard": None}
