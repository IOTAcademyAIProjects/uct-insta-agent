#!/usr/bin/env python3
"""
ClawAgent v3.0 Unified Command Line Interface
Hardened with SSRF, Path Traversal, and Input Sanitization Defenses.
"""

import sys
import os
import argparse
import json

# Ensure UTF-8 stdout encoding on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

from core.model_router import get_default_router
from core.security import (
    validate_safe_url, validate_safe_file_path,
    sanitize_handle, sanitize_user_input, SecurityException
)
from services.draft_service import DraftService
from services.brand_service import BrandService
from services.media_host import MediaHostService
from services.scheduler_service import SchedulerService
from services.engagement_service import EngagementService
from services.trend_service import TrendService
from services.competitor_service import CompetitorService
from services.repurpose_service import RepurposeService
from services.db_service import DBService
from agents.publisher_agent import PublisherAgent
from agents.creator_agent import CreatorAgent
from agents.designer_agent import DesignerAgent
from agents.analyst_agent import AnalystAgent
from agents.research_agent import ResearchAgent

def cmd_post(args):
    """Direct post without prior preview."""
    publisher = PublisherAgent()
    creator = CreatorAgent()
    
    try:
        img_url = validate_safe_url(args.url)
    except SecurityException as se:
        print(f"[SECURITY ERROR] {se}")
        return

    tone = sanitize_user_input(args.tone or "casual", max_length=50)
    platforms = [p.strip() for p in args.platforms.split(",")] if args.platforms else ["INSTAGRAM"]
    
    desc = sanitize_user_input(args.description, max_length=2000) if args.description else None
    if not desc:
        from agents.vision_agent import VisionAgent
        try:
            desc = VisionAgent().describe_image(img_url)
        except Exception:
            desc = "A visual post for our community"
            
    caption = creator.generate_caption(description=desc, tone=tone, platform=platforms[0])
    print(f"\n[Caption Generated]:\n{caption}\n")
    
    res = publisher.publish(media_urls=[img_url], caption=caption, platforms=platforms)
    for plat, r in res.items():
        if r.success:
            print(f"[SUCCESS] Posted to {plat}! Post ID: {r.post_id}")
            if r.permalink:
                print(f"URL: {r.permalink}")
        else:
            print(f"[FAILED] Failed on {plat}: {r.error}")

def cmd_carousel(args):
    """Post multi-image carousel."""
    publisher = PublisherAgent()
    creator = CreatorAgent()
    
    raw_urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    if len(raw_urls) < 2:
        print("[ERROR] Carousel requires at least 2 image URLs.")
        return
        
    try:
        urls = [validate_safe_url(u) for u in raw_urls]
    except SecurityException as se:
        print(f"[SECURITY ERROR] {se}")
        return

    tone = sanitize_user_input(args.tone or "casual", max_length=50)
    caption = creator.generate_carousel_caption(slide_count=len(urls), tone=tone)
    print(f"\n[Generated Carousel Caption]:\n{caption}\n")
    
    res = publisher.publish(media_urls=urls, caption=caption, media_type="CAROUSEL", platforms=["INSTAGRAM"])
    ig_res = res.get("INSTAGRAM")
    if ig_res and ig_res.success:
        print(f"[SUCCESS] Carousel posted to Instagram! Post ID: {ig_res.post_id}")
    else:
        print(f"[FAILED] {ig_res.error if ig_res else 'Unknown error'}")

def cmd_generate(args):
    """Generate AI image and create a draft preview."""
    designer = DesignerAgent()
    draft_service = DraftService()
    
    prompt = sanitize_user_input(args.prompt, max_length=1000)
    tone = sanitize_user_input(args.tone or "casual", max_length=50)
    
    print(f"Generating AI image for prompt: '{prompt}'...")
    img_data = designer.generate_image(prompt=prompt)
    img_url = img_data["image_url"]
    print(f"Image URL: {img_url}")
    
    draft = draft_service.create(
        image_url=img_url,
        tone=tone,
        description=prompt
    )
    
    print(f"\n--- Draft Preview #{draft['draft_id']} ---")
    print(f"DRAFT_ID: {draft['draft_id']}")
    print(f"IMAGE_URL: {img_url}")
    print(f"CAPTION: {draft['caption']}")
    print(f"\nTo post: python cli.py approve {draft['draft_id']}")
    print(f"To reject: python cli.py reject {draft['draft_id']}")

def cmd_preview(args):
    """Create draft from image URL with preview output."""
    try:
        url = validate_safe_url(args.url)
    except SecurityException as se:
        print(f"[SECURITY ERROR] {se}")
        return

    tone = sanitize_user_input(args.tone or "casual", max_length=50)
    desc = sanitize_user_input(args.description, max_length=2000) if args.description else None

    draft_service = DraftService()
    draft = draft_service.create(
        image_url=url,
        tone=tone,
        description=desc
    )
    print(f"DRAFT_ID: {draft['draft_id']}")
    print(f"IMAGE_URL: {draft['image_url']}")
    print(f"CAPTION: {draft['caption']}")

def cmd_approve(args):
    draft_service = DraftService()
    res = draft_service.approve(int(args.draft_id))
    if res.get("success"):
        print(f"[SUCCESS] Draft {args.draft_id} approved and published successfully!")
    else:
        print(f"[FAILED] Failed to approve draft: {res.get('error')}")

def cmd_reject(args):
    draft_service = DraftService()
    if draft_service.reject(int(args.draft_id)):
        print(f"Draft {args.draft_id} rejected and deleted.")
    else:
        print(f"[FAILED] Failed to reject draft {args.draft_id}")

def cmd_update(args):
    draft_service = DraftService()
    new_caption = sanitize_user_input(args.new_caption, max_length=2200)
    if draft_service.update_caption(int(args.draft_id), new_caption):
        print(f"Draft {args.draft_id} caption updated.")
    else:
        print(f"[FAILED] Failed to update draft {args.draft_id}")

def cmd_analytics(args):
    analyst = AnalystAgent()
    days = int(args.days) if args.days else 7
    res = analyst.analyze_performance(days=days)
    print(f"\nPerformance Analytics ({res['date_range']}):\n")
    print(res["summary"])

def cmd_brand(args):
    bs = BrandService()
    sub = args.subaction
    if sub == "list":
        brands = bs.list_all()
        print(f"Found {len(brands)} brand(s):")
        for b in brands:
            active = " [ACTIVE]" if b.get("is_active") else ""
            print(f"  * {b['name']}{active} (Tone: {b.get('tone_of_voice')})")
    elif sub == "switch":
        if not args.name:
            print("Usage: cli.py brand switch [name]")
            return
        if bs.switch_brand(args.name):
            print(f"[SUCCESS] Active brand switched to '{args.name}'.")
        else:
            print(f"[FAILED] Brand '{args.name}' not found.")
    elif sub == "create":
        if not args.name:
            print("Usage: cli.py brand create [name] [--tone tone]")
            return
        name = sanitize_user_input(args.name, max_length=50)
        tone = sanitize_user_input(args.tone or "casual", max_length=50)
        bid = bs.create(name, tone_of_voice=tone)
        print(f"[SUCCESS] Created brand '{name}' with ID {bid}.")
    elif sub == "analyze":
        brand = bs.get_active()
        print(f"Analyzing voice DNA for '{brand['name']}'...")
        res = bs.analyze_brand_voice(brand["id"])
        print("Brand Voice DNA extracted:")
        for k, v in res.items():
            print(f"  * {k}: {v}")

def cmd_competitors(args):
    cs = CompetitorService()
    ra = ResearchAgent()
    if args.add:
        try:
            handle = sanitize_handle(args.add)
            cs.add_competitor(handle)
            print(f"[SUCCESS] Added competitor: @{handle}")
        except SecurityException as se:
            print(f"[SECURITY ERROR] {se}")
    elif args.brief or not args.add:
        print("Competitor Intelligence Brief:\n")
        print(ra.analyze_competitors())

def cmd_trends(args):
    ts = TrendService()
    trends = ts.get_latest_trends()
    print("Trending Topics in Your Niche:\n")
    for t in trends:
        print(f"  * {t.get('topic')} ({t.get('source')}) - Velocity: {t.get('trend_velocity')}")

def cmd_ideas(args):
    ra = ResearchAgent()
    print("Weekly AI Content Strategy Brief:\n")
    print(ra.generate_weekly_brief())

def cmd_repurpose(args):
    rs = RepurposeService()
    text_input = args.text
    content = text_input
    
    # If text refers to a file, validate path safety against directory traversal
    if os.path.exists(text_input):
        try:
            safe_file = validate_safe_file_path(text_input)
            with open(safe_file, "r", encoding="utf-8") as f:
                content = f.read()
        except SecurityException as se:
            print(f"[SECURITY ERROR] Cannot read file: {se}")
            return
            
    print("Repurposing Content across Platforms...\n")
    res = rs.repurpose_article(content)
    print(json.dumps(res, indent=2))

def cmd_ai_status(args):
    router = get_default_router()
    status = router.get_status()
    print("Model Providers & Health Status:\n")
    for name, s in status.items():
        creds = "Key Set" if s["has_credentials"] else "No Key"
        state = s["circuit_state"]
        print(f"  * {name.ljust(14)} | {creds.ljust(8)} | Circuit: {state.ljust(10)} | Model: {s.get('model')}")

def cmd_db(args):
    dbs = DBService()
    sub = args.subaction
    if sub == "storage":
        stats = dbs.get_stats()
        print("\nDatabase Storage Report")
        print("=======================")
        for k, v in stats.items():
            print(f"{k.ljust(18)}: {v}")
    elif sub == "history":
        rows = dbs.get_history()
        print(f"Last {len(rows)} posts:")
        for r in rows:
            print(f"  [{r[0]}] {r[5][:10] if len(r)>5 else ''} | {r[3]} | ID: {r[1]}")
    elif sub == "drafts":
        rows = dbs.get_drafts()
        print(f"{len(rows)} pending draft(s):")
        for r in rows:
            print(f"  [{r[0]}] {r[5][:16] if len(r)>5 else ''} | {r[4]} | Tone: {r[3]}")
    elif sub == "ai_stats":
        rows = dbs.get_ai_stats()
        print("AI Provider Call Metrics:")
        for r in rows:
            print(f"  * {r['provider']}: {r['calls']} calls, {r['successful']} successful, avg {int(r.get('avg_latency') or 0)}ms")

def main():
    parser = argparse.ArgumentParser(description="ClawAgent v3.0 CLI")
    subparsers = parser.add_subparsers(dest="command")

    # post
    p_post = subparsers.add_parser("post")
    p_post.add_argument("url", help="Media URL")
    p_post.add_argument("--tone", default="casual")
    p_post.add_argument("--platforms", default="INSTAGRAM")
    p_post.add_argument("--description", default=None)

    # carousel
    p_car = subparsers.add_parser("carousel")
    p_car.add_argument("urls", help="Comma-separated image URLs")
    p_car.add_argument("--tone", default="casual")

    # generate
    p_gen = subparsers.add_parser("generate")
    p_gen.add_argument("prompt", help="Image generation prompt")
    p_gen.add_argument("--tone", default="casual")

    # preview / approve / reject / update
    p_prev = subparsers.add_parser("preview")
    p_prev.add_argument("url")
    p_prev.add_argument("--tone", default="casual")
    p_prev.add_argument("--description", default=None)

    p_app = subparsers.add_parser("approve")
    p_app.add_argument("draft_id")

    p_rej = subparsers.add_parser("reject")
    p_rej.add_argument("draft_id")

    p_upd = subparsers.add_parser("update")
    p_upd.add_argument("draft_id")
    p_upd.add_argument("new_caption")

    # analytics
    p_ana = subparsers.add_parser("analytics")
    p_ana.add_argument("--days", default=7)

    # brand
    p_br = subparsers.add_parser("brand")
    p_br.add_argument("subaction", choices=["list", "switch", "create", "analyze"])
    p_br.add_argument("name", nargs="?", default=None)
    p_br.add_argument("--tone", default="casual")

    # competitors
    p_comp = subparsers.add_parser("competitors")
    p_comp.add_argument("--add", default=None)
    p_comp.add_argument("--brief", action="store_true")

    # trends & ideas
    subparsers.add_parser("trends")
    subparsers.add_parser("ideas")

    # repurpose
    p_rep = subparsers.add_parser("repurpose")
    p_rep.add_argument("text", help="Article text or file path")

    # status & db
    subparsers.add_parser("ai-status")

    p_db = subparsers.add_parser("db")
    p_db.add_argument("subaction", choices=["storage", "history", "drafts", "ai_stats"])

    args = parser.parse_args()

    if args.command == "post":
        cmd_post(args)
    elif args.command == "carousel":
        cmd_carousel(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "preview":
        cmd_preview(args)
    elif args.command == "approve":
        cmd_approve(args)
    elif args.command == "reject":
        cmd_reject(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "analytics":
        cmd_analytics(args)
    elif args.command == "brand":
        cmd_brand(args)
    elif args.command == "competitors":
        cmd_competitors(args)
    elif args.command == "trends":
        cmd_trends(args)
    elif args.command == "ideas":
        cmd_ideas(args)
    elif args.command == "repurpose":
        cmd_repurpose(args)
    elif args.command == "ai-status":
        cmd_ai_status(args)
    elif args.command == "db":
        cmd_db(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
