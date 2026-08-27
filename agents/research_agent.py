"""
Research Agent v2: Competitor Monitoring, Trend Synthesis & Weekly Strategy Briefs
Implements analyst-grade JSON brief with content_ideas persistence and graceful fallback.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from core.model_router import get_default_router
from core.security import extract_json_from_llm, sanitize_user_input, mask_secrets
from services.competitor_service import CompetitorService
from services.trend_service import TrendService
from services.brand_service import BrandService
from prompts.competitor import build_competitor_analysis_prompt
from prompts.trend import build_trend_synthesis_prompt
from db.repository import get_connection

logger = logging.getLogger("clawagent.research")

def _fallback_brief(brand_name: str, trends_text: str, comp_text: str) -> str:
    """Curated template when no LLM provider available — still actionable."""
    return (
        f"📊 Weekly Content Intelligence — Week {datetime.now(timezone.utc).isocalendar().week}\n\n"
        f"🔥 Trending in your niche:\n{trends_text}\n\n"
        f"👀 Competitor spotlight:\n{comp_text}\n\n"
        "💡 Content ideas for this week:\n"
        "  1. Carousel: '5 mistakes to avoid' — educational swipe (IG Carousel)\n"
        "  2. Reel: 30s hook with trending audio — tip demo (IG Reel)\n"
        "  3. LinkedIn post: Founder story behind product — authenticity (LinkedIn)\n"
        "  4. Story poll: 'Which feature should we build next?' — engagement (IG Story)\n"
        "  5. X Thread: 'The future of smart content in India — a thread 🧵' (X)\n\n"
        f"Generated for {brand_name} via curated fallback (set GEMINI_API_KEY or MISTRAL_API_KEY for AI-powered brief)."
    )

class ResearchAgent:
    def __init__(self):
        self.router = get_default_router()
        self.competitor_service = CompetitorService()
        self.trend_service = TrendService()
        self.brand_service = BrandService()

    def _persist_content_ideas(self, brand_id: int, ideas: List[Dict[str, Any]], source_trend_id: Optional[int] = None):
        """Persists 5 ideas to content_ideas table with year-week."""
        now = datetime.now(timezone.utc)
        year, week, _ = now.isocalendar()
        week_num = year * 100 + week
        conn = get_connection()
        try:
            for idea in ideas[:5]:
                # Support both old flat and new structured idea
                if isinstance(idea, str):
                    idea_text = idea
                    draft_caption = idea
                    suggested_media = "AI visual"
                    target_platform = "INSTAGRAM"
                else:
                    idea_text = idea.get("topic") or idea.get("title") or idea.get("idea_text") or str(idea)[:120]
                    draft_caption = idea.get("draft_hook") or idea.get("draft_caption") or idea.get("hook") or idea_text
                    suggested_media = idea.get("suggested_media") or idea.get("visual") or idea.get("format") or "carousel"
                    target_platform = (idea.get("platform") or idea.get("target_platform") or "INSTAGRAM").upper()
                    # Normalize platform
                    if target_platform not in ["INSTAGRAM","LINKEDIN","TWITTER","YOUTUBE","FACEBOOK"]:
                        target_platform = "INSTAGRAM"
                try:
                    conn.execute(
                        """INSERT INTO content_ideas (brand_id, week_number, idea_text, draft_caption, suggested_media, target_platform, source_trend_id, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, 'SUGGESTED')""",
                        (brand_id, week_num, idea_text[:500], draft_caption[:500], suggested_media[:300], target_platform, source_trend_id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to persist idea: {mask_secrets(str(e))}")
            conn.commit()
        finally:
            conn.close()

    def generate_weekly_brief(self, brand_id: Optional[int] = None) -> str:
        """Synthesizes competitor data + trending topics + own analytics into weekly brief. Persists ideas."""
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        brand_name = brand.get("name", "Brand") if brand else "Brand"
        b_id = brand.get("id", 1) if brand else 1
        
        # 1. Fetch trends (relevance sorted, TTL filtered)
        trends = self.trend_service.get_latest_trends(b_id)
        if not trends:
            trends = self.trend_service.fetch_trending_topics(brand_niche=brand_name)
        trends_text = "\n".join([f"- {t.get('topic')} ({t.get('trend_velocity')}, {t.get('source')}, score {t.get('relevance_score',0.85)})" for t in trends[:5]])
        if not trends_text:
            trends_text = "- No fresh signals this week"
        
        # 2. Fetch competitors + gap data
        competitors = self.competitor_service.list_competitors(b_id)
        gap_data = self.competitor_service.get_gap_analysis_data(b_id)
        comp_text = "\n".join([f"- @{c.get('handle')} ({c.get('platform')}) — avg {c.get('avg_engagement_rate',0):.1%} last sync {c.get('last_scraped_at','never')}" for c in competitors]) if competitors else "No competitors tracked yet. Use `python cli.py competitors --add @handle`."
        # Add recent competitor themes if any
        if gap_data.get("recent_posts"):
            comp_themes = gap_data.get("themes", {})
            theme_line = ", ".join([f"{k} ({v})" for k,v in list(comp_themes.items())[:3]]) if comp_themes else "diverse topics"
            comp_text += f"\n  Recent themes: {theme_line} — {gap_data['post_count_7d']} posts in last 7d"
        
        # 3. Fetch own performance (graceful fallback if Analyst needs LLM)
        own_perf_text = "Consistent posting, high save rate on carousels."
        try:
            from agents.analyst_agent import AnalystAgent
            analyst = AnalystAgent()
            # Attempt to get summary but don't fail brief if LLM down
            perf = analyst.analyze_performance(days=7, brand_id=b_id)
            # perf may be dict with summary
            own_perf_text = perf.get("summary", own_perf_text)[:500]
        except Exception as e:
            logger.info(f"Own performance fetch for brief used fallback: {mask_secrets(str(e))}")

        # 4. Build synthesis prompt — request strict JSON for downstream persistence, but also render fallback markdown
        sys_p, user_p = build_trend_synthesis_prompt(
            brand_name=brand_name,
            brand_niche=brand.get("tone_of_voice","Growth & Digital Media")[:80],
            trends_data_text=f"TRENDS:\n{trends_text}\n\nTRACKED COMPETITORS:\n{comp_text}\n\nOWN PERFORMANCE (7d):\n{own_perf_text}\n\nBRAND VOICE: {brand.get('tone_of_voice','casual')}"
        )
        # Augment to request structured JSON + markdown
        json_instruction = (
            "\n\nOUTPUT INSTRUCTIONS:\n"
            "Return STRICT JSON with keys: { \"performance_summary\": \"2 sentences\", \"competitor_spotlight\": \"1 paragraph\", \"trending\": [\"topic1\",\"topic2\",\"topic3\"], \"content_ideas\": [{\"topic\":\"...\",\"platform\":\"INSTAGRAM|LINKEDIN|TWITTER|YOUTUBE\",\"format\":\"CAROUSEL|REEL|POST|THREAD\",\"draft_hook\":\"...\",\"suggested_media\":\"...\",\"why\":\"...\"} x5 ] }\n"
            "After the JSON, also include a markdown brief header '📊 Weekly Content Intelligence — Week N' for human reading. JSON first, markdown after."
        )
        enhanced_user = user_p + json_instruction

        # 5. Route to deep_analysis / reasoning with fallback
        raw = None
        last_err = None
        for task_type in ["deep_analysis", "reasoning"]:
            try:
                raw = self.router.generate_text(
                    task_type=task_type,
                    prompt=enhanced_user,
                    system_prompt=sys_p,
                    max_tokens=900
                )
                if raw:
                    break
            except Exception as e:
                last_err = mask_secrets(str(e))
                logger.info(f"Brief generation via {task_type} failed: {last_err}")
                continue

        if not raw:
            # Curated fallback — still persist ideas
            fallback = _fallback_brief(brand_name, trends_text, comp_text)
            # Persist 5 curated ideas
            curated_ideas = [
                {"topic": "5 mistakes to avoid", "platform": "INSTAGRAM", "format": "CAROUSEL", "draft_hook": "5 mistakes you're making with...", "suggested_media": "carousel 5 slides"},
                {"topic": "Trending audio tip", "platform": "INSTAGRAM", "format": "REEL", "draft_hook": "POV: you finally found the hack for...", "suggested_media": "30s reel"},
                {"topic": "Founder story", "platform": "LINKEDIN", "format": "POST", "draft_hook": "Why we chose...", "suggested_media": "single image"},
                {"topic": "Poll engagement", "platform": "INSTAGRAM", "format": "STORY", "draft_hook": "Which feature next?", "suggested_media": "story poll"},
                {"topic": "Future thread", "platform": "TWITTER", "format": "THREAD", "draft_hook": "The future of ... 🧵", "suggested_media": "text thread"},
            ]
            source_trend_id = trends[0].get("id") if trends else None
            self._persist_content_ideas(b_id, curated_ideas, source_trend_id)
            return fallback

        # 6. Try to extract JSON + persist ideas, otherwise treat raw as markdown brief
        try:
            parsed = extract_json_from_llm(raw)
            # parsed may be dict with content_ideas
            ideas = None
            if isinstance(parsed, dict):
                ideas = parsed.get("content_ideas") or parsed.get("ideas") or parsed.get("contentIdeas")
            elif isinstance(parsed, list):
                ideas = parsed
            if ideas and isinstance(ideas, list):
                source_trend_id = trends[0].get("id") if trends else None
                self._persist_content_ideas(b_id, ideas, source_trend_id)
                # If JSON parsed, reconstruct human markdown if not in raw tail
                if "📊 Weekly" not in raw:
                    md = (
                        f"📊 Weekly Content Intelligence — Week {datetime.now(timezone.utc).isocalendar().week}\n\n"
                        f"Performance: {parsed.get('performance_summary','')}\n\n"
                        f"Competitor spotlight: {parsed.get('competitor_spotlight','')}\n\n"
                        f"Trending: {', '.join(parsed.get('trending',[]))}\n\n"
                        f"💡 Ideas:\n"
                    )
                    for i, idea in enumerate(ideas[:5], 1):
                        if isinstance(idea, dict):
                            md += f"  {i}. {idea.get('topic','Idea')} ({idea.get('platform','IG')} {idea.get('format','POST')}): {idea.get('draft_hook','')}\n"
                        else:
                            md += f"  {i}. {idea}\n"
                    return md
            # If no ideas extracted, still check for weekly header
            if "📊 Weekly" in raw or len(raw) > 100:
                return raw
            # Fallback to parsing entire raw
            return raw
        except Exception as e:
            logger.info(f"Brief JSON extraction used raw markdown: {mask_secrets(str(e))}")
            # Still attempt to persist if raw contains 5 ideas heuristically — but skip if no JSON
            return raw

    def analyze_competitors(self, brand_id: Optional[int] = None) -> str:
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        brand_name = brand.get("name", "Brand") if brand else "Brand"
        b_id = brand.get("id", 1) if brand else 1
        
        competitors = self.competitor_service.list_competitors(b_id)
        if not competitors:
            return "No competitor handles tracked yet. Use `python cli.py competitors --add @handle` to start tracking!"

        gap = self.competitor_service.get_gap_analysis_data(b_id)
        recent = gap.get("recent_posts", [])
        themes = gap.get("themes", {})
        comp_text = "\n".join([f"- @{c.get('handle')} on {c.get('platform')} — avg {c.get('avg_engagement_rate',0):.1%} | last {c.get('last_scraped_at','never')}" for c in competitors])
        if recent:
            comp_text += "\n\nRecent competitor posts (last 7d):\n" + "\n".join([f"  • {p.get('handle')}: {p.get('caption_summary','')[:80]} ({p.get('estimated_engagement',0):.1%})" for p in recent[:5]])
            if themes:
                comp_text += "\n\nTop themes: " + ", ".join([f"{k} x{v}" for k,v in themes.items()])

        # Own performance for context
        own_perf = "Consistent posting, high save rate on carousels."
        try:
            from agents.analyst_agent import AnalystAgent
            perf = AnalystAgent().analyze_performance(days=7, brand_id=b_id)
            own_perf = perf.get("summary", own_perf)[:400]
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")

        sys_p, user_p = build_competitor_analysis_prompt(
            brand_name=brand_name,
            competitor_data_text=comp_text,
            own_performance_text=own_perf
        )

        # Try LLM with fallback
        for task in ["deep_analysis", "reasoning"]:
            try:
                return self.router.generate_text(
                    task_type=task,
                    prompt=user_p,
                    system_prompt=sys_p,
                    max_tokens=500
                )
            except Exception as e:
                logger.info(f"Competitor analysis via {task} failed: {mask_secrets(str(e))}")
                continue

        # Fallback markdown
        return (
            f"👀 Competitor Gap Analysis for {brand_name}\n\n"
            f"{comp_text}\n\n"
            f"Own performance: {own_perf}\n\n"
            "Counter-moves (curated):\n"
            "1. Post carousel '5 mistakes' to counter their educational series\n"
            "2. Publish founder story to own authenticity gap\n"
            "3. Test trending audio reel to match their velocity\n\n"
            "(Set GEMINI_API_KEY or MISTRAL_API_KEY for AI depth)"
        )
