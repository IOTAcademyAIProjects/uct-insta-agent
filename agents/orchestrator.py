"""
Orchestrator Agent: Central Intent Classification & Specialist Dispatch
Hardened with Resilient JSON Extraction & Heuristic Fallbacks.
"""

import logging
from typing import Dict, Any, Tuple

from core.model_router import get_default_router
from core.security import extract_json_from_llm
from prompts.orchestrator import build_intent_classification_prompt

logger = logging.getLogger("clawagent.orchestrator")

class OrchestratorAgent:
    def __init__(self):
        self.router = get_default_router()

    def classify_and_route(self, user_message: str) -> Dict[str, Any]:
        """Classifies intent using the fast Cerebras model and extracts arguments."""
        sys_p, user_p = build_intent_classification_prompt(user_message)
        
        try:
            raw_response = self.router.generate_text(
                task_type="orchestration",
                prompt=user_p,
                system_prompt=sys_p,
                max_tokens=100,
                temperature=0.1
            )
            return extract_json_from_llm(raw_response)
        except Exception as e:
            logger.warning(f"Fast intent classification failed ({e}), falling back to heuristic parsing.")
            return self._heuristic_fallback(user_message)

    def _heuristic_fallback(self, msg: str) -> Dict[str, Any]:
        msg_lower = msg.lower()
        if "carousel" in msg_lower:
            return {"intent": "CAROUSEL", "params": {}}
        elif "story" in msg_lower:
            return {"intent": "STORY", "params": {}}
        elif "analytic" in msg_lower or "stat" in msg_lower or "report" in msg_lower:
            return {"intent": "ANALYTICS", "params": {}}
        elif "dm" in msg_lower or "message" in msg_lower:
            return {"intent": "DMS", "params": {}}
        elif "generate" in msg_lower or "image" in msg_lower:
            return {"intent": "GENERATE_IMAGE", "params": {}}
        elif "trend" in msg_lower or "idea" in msg_lower:
            return {"intent": "TRENDS", "params": {}}
        elif "competitor" in msg_lower:
            return {"intent": "COMPETITORS", "params": {}}
        elif "brand" in msg_lower:
            return {"intent": "BRAND", "params": {}}
        else:
            return {"intent": "POST", "params": {}}
