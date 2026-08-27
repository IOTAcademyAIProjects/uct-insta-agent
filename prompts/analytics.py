"""
Prompt Templates for Analytics & Performance Interpretation
"""

def build_analytics_prompt(data_text: str, ranking_text: str, date_range: str, brand_name: str = "Brand") -> tuple[str, str]:
    system_prompt = (
        f"You are the senior data analyst and growth strategist for {brand_name}.\n"
        "Transform raw engagement metrics into plain-English, high-impact growth insights for Telegram.\n"
        "Be concise, actionable, and focus on strategic ROI."
    )
    user_prompt = (
        f"Instagram Performance Report for: {date_range}\n\n"
        f"RAW METRICS DATA:\n{data_text}\n\n"
        f"CONTENT TYPE ENGAGEMENT RANKING:\n{ranking_text}\n\n"
        f"Provide an executive summary:\n"
        f"1. 🏆 Top Performer: Best post and the psychological reason it won\n"
        f"2. 📈 Key Trend: Audience reach velocity and saves/shares signals\n"
        f"3. 🎯 Winning Format: Which content format (Image/Video/Carousel) to double down on\n"
        f"4. 💡 Immediate Action: 1 concrete creative tactic to test on the next post"
    )
    return system_prompt, user_prompt
