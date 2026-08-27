"""
Research Agent: Competitor Monitoring, Trend Synthesis & Strategy Briefs
"""

import logging
from typing import Dict, Any, Optional, List

from core.model_router import get_default_router
from services.competitor_service import CompetitorService
from services.trend_service import TrendService
from services.brand_service import BrandService
from prompts.competitor import build_competitor_analysis_prompt
from prompts.trend import build_trend_synthesis_prompt

logger = logging.getLogger("clawagent.research")

class ResearchAgent:
    def __init__(self):
        self.router = get_default_router()
        self.competitor_service = CompetitorService()
        self.trend_service = TrendService()
        self.brand_service = BrandService()

    def generate_weekly_brief(self, brand_id: Optional[int] = None) -> str:
        """Synthesizes competitor data and trending topics into an actionable strategy brief."""
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        brand_name = brand.get("name", "Brand") if brand else "Brand"
        
        # 1. Fetch trends
        trends = self.trend_service.get_latest_trends(brand.get("id", 1) if brand else 1)
        trends_text = "\n".join([f"- {t.get('topic')} ({t.get('trend_velocity')})" for t in trends])
        
        # 2. Fetch competitors
        competitors = self.competitor_service.list_competitors(brand.get("id", 1) if brand else 1)
        comp_text = "\n".join([f"- @{c.get('handle')} ({c.get('platform')})" for c in competitors]) if competitors else "No competitors tracked yet."

        sys_p, user_p = build_trend_synthesis_prompt(
            brand_name=brand_name,
            brand_niche="Growth & Digital Media",
            trends_data_text=f"TRENDS:\n{trends_text}\n\nTRACKED COMPETITORS:\n{comp_text}"
        )

        return self.router.generate_text(
            task_type="deep_analysis",
            prompt=user_p,
            system_prompt=sys_p,
            max_tokens=500
        )

    def analyze_competitors(self, brand_id: Optional[int] = None) -> str:
        brand = self.brand_service.get_by_id(brand_id) if brand_id else self.brand_service.get_active()
        brand_name = brand.get("name", "Brand") if brand else "Brand"
        
        competitors = self.competitor_service.list_competitors(brand.get("id", 1) if brand else 1)
        if not competitors:
            return "No competitor handles tracked yet. Use `/competitors --add @handle` to start tracking!"

        comp_text = "\n".join([f"- @{c.get('handle')} on {c.get('platform')}" for c in competitors])
        sys_p, user_p = build_competitor_analysis_prompt(
            brand_name=brand_name,
            competitor_data_text=comp_text,
            own_performance_text="Consistent posting, high save rate on carousels."
        )

        return self.router.generate_text(
            task_type="deep_analysis",
            prompt=user_p,
            system_prompt=sys_p,
            max_tokens=450
        )
