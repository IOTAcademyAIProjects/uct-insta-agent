"""
Telegram Bot — Polling + Webhook entrypoint
Uses python-telegram-bot if available, else stub for testing.
Implements HITL draft flow with inline keyboards.
"""

import os
import logging
from typing import Optional

from core.security import sanitize_user_input, validate_safe_url, SecurityException
from services.draft_service import DraftService
from services.brand_service import BrandService
from telegram.keyboards import build_draft_keyboard, build_brand_keyboard, build_analytics_keyboard, build_self_improve_keyboard, to_telegram_markup, render_draft_preview_text, render_self_improve_text
from telegram.callbacks import handle_callback

logger = logging.getLogger("clawagent.telegram.bot")

# Allowlist check — fail-closed by default
def is_allowed_user(user_id: str) -> bool:
    # Explicit dev open flag
    if os.getenv("ALLOW_OPEN", "").lower() in ("1", "true", "yes"):
        logger.warning("ALLOW_OPEN enabled — allowing all Telegram users (dev only)")
        return True
    allowed = os.getenv("TELEGRAM_ALLOW_FROM") or os.getenv("TELEGRAM_NOTIFY_CHAT_ID") or ""
    if not allowed:
        # Fallback to openclaw-config/openclaw.json files
        try:
            import json
            for cfg_path in ["openclaw-config/openclaw.json", ".openclaw/openclaw.json", "openclaw.json"]:
                if os.path.exists(cfg_path):
                    with open(cfg_path) as f:
                        cfg = json.load(f)
                        chan = cfg.get("channels", {}).get("telegram", {})
                        allowed_list = chan.get("allowFrom") or chan.get("allow_from") or []
                        if str(user_id) in [str(x) for x in allowed_list]:
                            return True
        except Exception:
            pass
        # No allowlist configured → deny (fail-closed)
        logger.warning("No Telegram allowlist configured — denying user %s (set TELEGRAM_ALLOW_FROM or ALLOW_OPEN=true for dev)", user_id)
        return False
    allowed_list = [x.strip() for x in allowed.split(",") if x.strip()]
    return str(user_id) in allowed_list

# --- Core handler logic (testable without SDK) ---

def handle_photo_message(image_url: str, tone: str = "casual", description: Optional[str] = None, user_id: str = None) -> dict:
    """Creates draft from image URL, returns {text, keyboard, draft}"""
    if user_id and not is_allowed_user(user_id):
        return {"text": "⛔ Unauthorized. Ask admin to allowlist your Telegram ID.", "keyboard": None}
    try:
        safe_url = validate_safe_url(image_url)
    except SecurityException as se:
        return {"text": f"⛔ URL blocked: {se}", "keyboard": None}
    tone_clean = sanitize_user_input(tone or "casual", max_length=50)
    desc_clean = sanitize_user_input(description, max_length=2000) if description else None

    ds = DraftService()
    brand = BrandService().get_active()
    try:
        draft = ds.create(
            image_url=safe_url,
            tone=tone_clean,
            description=desc_clean,
            brand_id=brand.get("id", 1) if brand else 1
        )
        # Fetch full draft row for rendering
        from db.repository import get_draft
        full = get_draft(draft["draft_id"]) or draft
        # Check compliance
        compliance = None
        try:
            bs = BrandService()
            ok, issues = bs.check_compliance(draft.get("caption",""), brand.get("id") if brand else None)
            compliance = {"score": 0.95 if ok else 0.6, "issues": issues}
        except Exception:
            pass
        text = render_draft_preview_text(full, brand_name=brand.get("name","Brand") if brand else "Brand", compliance=compliance)
        # Add variants count
        variants = draft.get("caption_variants") or []
        kb = build_draft_keyboard(draft["draft_id"], has_variants=len(variants)>1)
        return {"text": text, "keyboard": kb, "draft": draft, "draft_id": draft["draft_id"]}
    except Exception as e:
        logger.error(f"Draft creation failed: {e}")
        return {"text": f"❌ Draft failed: {e}", "keyboard": None}

def handle_brand_command(subaction: str = "list", name: str = None, user_id: str = None) -> dict:
    bs = BrandService()
    if subaction == "list":
        brands = bs.list_all()
        active = bs.get_active()
        active_name = active.get("name") if active else None
        kb = build_brand_keyboard(brands, active_name=active_name)
        lines = "\n".join([f"{'✅' if b.get('name')==active_name else '  '} {b.get('name')} ({b.get('tone_of_voice')})" for b in brands])
        return {"text": f"🏷️ Brands ({len(brands)}):\n{lines}", "keyboard": kb}
    elif subaction == "switch" and name:
        if bs.switch_brand(name):
            return {"text": f"✅ Switched to {name}", "keyboard": None}
        return {"text": f"❌ Brand {name} not found", "keyboard": None}
    return {"text": "Usage: /brand list | /brand switch <name>", "keyboard": None}

def handle_improve_command(subaction: str = "propose", proposal_id: str = None, user_id: str = None) -> dict:
    from services.self_improvement_service import SelfImprovementService
    svc = SelfImprovementService()
    if subaction == "propose":
        res = svc.propose(dry_run=True)
        if not res.get("proposed"):
            return {"text": f"ℹ️ {res.get('reason')}", "keyboard": None}
        p = res["proposal"]
        text = render_self_improve_text(p)
        kb = build_self_improve_keyboard(p["id"])
        return {"text": text, "keyboard": kb, "proposal": p}
    elif subaction == "list":
        pending = svc.list_pending()
        if not pending:
            return {"text": "No pending proposals. Use /improve propose", "keyboard": None}
        lines = "\n".join([f"#{p['id']} {p['changed_field']} {p['old_value'][:20]}→{p['new_value'][:20]} {p['status']}" for p in pending[:5]])
        kb = build_self_improve_keyboard(pending[0]["id"]) if pending else None
        return {"text": f"🧬 Pending ({len(pending)}):\n{lines}", "keyboard": kb}
    elif subaction == "view" and proposal_id:
        try:
            from db.repository import get_connection
            conn = get_connection()
            row = conn.execute("SELECT * FROM improvement_log WHERE id=?", (int(proposal_id),)).fetchone()
            conn.close()
            if not row:
                return {"text": f"Proposal {proposal_id} not found", "keyboard": None}
            text = render_self_improve_text(dict(row))
            kb = build_self_improve_keyboard(int(proposal_id))
            return {"text": text, "keyboard": kb}
        except Exception as e:
            return {"text": f"Error: {e}", "keyboard": None}
    elif subaction == "history":
        hist = svc.get_history(limit=5)
        if not hist:
            return {"text": "No history yet.", "keyboard": None}
        lines = "\n".join([f"#{h['id']} {h['changed_field']} {h['status']} lift {h.get('predicted_lift',0):.0%} → {h.get('metric_after',0):.2f}" for h in hist])
        return {"text": f"📈 History:\n{lines}", "keyboard": None}
    return {"text": "Usage: /improve propose | /improve list | /improve view <id> | /improve history", "keyboard": None}

# --- SDK wiring (only if python-telegram-bot installed) ---

def create_application():
    """Creates Telegram Application if SDK present and token set."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.info("TELEGRAM_BOT_TOKEN not set — bot not started (CLI mode only)")
        return None
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

        app = Application.builder().token(token).build()

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed_user(update.effective_user.id):
                await update.message.reply_text("⛔ Unauthorized")
                return
            await update.message.reply_text("ClawAgent v3.0 — send a photo or image URL to create a draft preview. Commands: /brand /analytics /trends /ideas")

        async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed_user(update.effective_user.id):
                await update.message.reply_text("⛔ Unauthorized")
                return
            # Prefer file_id URL or caption URL
            image_url = None
            if update.message.photo:
                # Get largest photo file
                photo = update.message.photo[-1]
                file = await context.bot.get_file(photo.file_id)
                # file.file_path is relative like "photos/file_57.jpg" — build full Telegram file URL
                if file.file_path and file.file_path.startswith("http"):
                    image_url = file.file_path
                elif file.file_path:
                    image_url = f"https://api.telegram.org/file/bot{token}/{file.file_path}"
                else:
                    image_url = None
            elif update.message.text:
                # Extract URL from text
                import re
                m = re.search(r"https?://\S+", update.message.text)
                if m:
                    image_url = m.group(0)
            if not image_url:
                await update.message.reply_text("Send a photo or image URL to create a draft.")
                return
            tone = "casual"
            if update.message.caption:
                tone = update.message.caption.split()[0]
            res = handle_photo_message(image_url, tone=tone, user_id=str(update.effective_user.id))
            markup = to_telegram_markup(res["keyboard"]) if res.get("keyboard") else None
            await update.message.reply_text(res["text"], reply_markup=markup)

        async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed_user(update.effective_user.id):
                return
            text = update.message.text or ""
            # Simple URL detection for draft flow
            import re
            if re.search(r"https?://\S+", text):
                res = handle_photo_message(re.search(r"https?://\S+", text).group(0), tone="casual", user_id=str(update.effective_user.id))
                markup = to_telegram_markup(res["keyboard"]) if res.get("keyboard") else None
                await update.message.reply_text(res["text"], reply_markup=markup)
            else:
                await update.message.reply_text("Send an image URL or photo. Use /brand list to switch brands.")

        async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            if not is_allowed_user(query.from_user.id):
                await query.edit_message_text("⛔ Unauthorized")
                return
            res = handle_callback(query.data, user_id=str(query.from_user.id))
            markup = to_telegram_markup(res["keyboard"]) if res.get("keyboard") else None
            # If posted, edit original with result
            try:
                await query.edit_message_text(res["text"], reply_markup=markup)
            except Exception:
                await query.message.reply_text(res["text"], reply_markup=markup)

        async def brand_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed_user(update.effective_user.id):
                await update.message.reply_text("⛔ Unauthorized")
                return
            args = context.args
            sub = args[0] if args else "list"
            name = args[1] if len(args) >1 else None
            res = handle_brand_command(sub, name, user_id=str(update.effective_user.id))
            markup = to_telegram_markup(res["keyboard"]) if res.get("keyboard") else None
            await update.message.reply_text(res["text"], reply_markup=markup)

        async def analytics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed_user(update.effective_user.id):
                await update.message.reply_text("⛔ Unauthorized")
                return
            kb = build_analytics_keyboard()
            await update.message.reply_text("📊 Choose range:", reply_markup=to_telegram_markup(kb))

        async def improve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not is_allowed_user(update.effective_user.id):
                await update.message.reply_text("⛔ Unauthorized")
                return
            args = context.args
            sub = args[0] if args else "propose"
            pid = args[1] if len(args)>1 else None
            res = handle_improve_command(sub, pid, user_id=str(update.effective_user.id))
            markup = to_telegram_markup(res["keyboard"]) if res.get("keyboard") else None
            await update.message.reply_text(res["text"], reply_markup=markup)

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("brand", brand_cmd))
        app.add_handler(CommandHandler("analytics", analytics_cmd))
        app.add_handler(CommandHandler("improve", improve_cmd))
        app.add_handler(MessageHandler(filters.PHOTO, on_photo))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
        app.add_handler(CallbackQueryHandler(on_callback))

        return app
    except ImportError as e:
        logger.warning(f"python-telegram-bot not installed: {e} — bot stub only")
        return None
    except Exception as e:
        logger.error(f"Failed to create Telegram app: {e}")
        return None

def run_polling():
    app = create_application()
    if not app:
        print("Telegram bot not configured (set TELEGRAM_BOT_TOKEN). Running in CLI-only mode.")
        return
    print("Starting Telegram bot polling...")
    app.run_polling()

if __name__ == "__main__":
    run_polling()
