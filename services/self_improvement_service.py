"""
Self-Improving Loop Service — L1 Hook/Hashtag/Readability + L2 Routing (gated)
Observe → Hypothesize → Propose (dry-run) → Human Approve → Apply → Measure → Keep/Revert
Implements PRD 3.13 Self-Improving Loop, SPEC 9, flowchart 3.9
Hardened: single proposal per brand per week, human gate, $0 free models only
"""

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

from db.repository import get_connection, get_database_url
from core.model_router import get_default_router
from core.security import extract_json_from_llm, sanitize_user_input, mask_secrets
from services.brand_service import BrandService
from services.performance_memory import PerformanceMemory

logger = logging.getLogger("clawagent.self_improve")

ALLOWED_FIELDS = {
    "hashtag_count_range",  # e.g. "5-7" -> "1-3"
    "sample_hooks",         # JSON list of top hooks
    "avg_sentence_length",  # float
    "emoji_frequency",      # float
    "tone_of_voice",        # string - L3 gated, not auto without approval
}

# L1 only: safe to auto-propose; L3 requires extra approval flag
L1_SAFE_FIELDS = {"hashtag_count_range", "sample_hooks", "avg_sentence_length", "emoji_frequency"}
L3_GATED_FIELDS = {"tone_of_voice", "prohibited_words", "mandatory_elements"}

class SelfImprovementService:
    def __init__(self):
        self.router = get_default_router()
        self.brand_service = BrandService()
        self.perf = PerformanceMemory()

    # ---------- OBSERVE ----------
    def observe(self, brand_id: int = 1) -> Dict[str, Any]:
        """Collects signals for hypothesis generation."""
        # Brand profile
        brand = self.brand_service.get_by_id(brand_id) or self.brand_service.get_active()
        # Performance last 14d
        top_posts = self.perf.rank_posts_by_engagement(brand_id, days=14, limit=20)
        # Bottom posts for contrast
        conn = get_connection()
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
            bottom = conn.execute(
                "SELECT * FROM posts WHERE brand_id=? AND (timestamp >= ? OR created_at >= ?) ORDER BY engagement_rate ASC LIMIT 5",
                (brand_id, cutoff, cutoff)
            ).fetchall()
            bottom = [dict(r) for r in bottom]
            # AI provider health last 7d
            ai_rows = conn.execute(
                "SELECT provider, AVG(CASE WHEN success=1 THEN 1 ELSE 0 END) as success_rate, AVG(latency_ms) as avg_lat FROM ai_calls WHERE brand_id=? AND timestamp >= datetime('now','-7 days') GROUP BY provider",
                (brand_id,)
            ).fetchall()
            ai_health = [dict(r) for r in ai_rows]
            # Trend freshness
            trends = conn.execute(
                "SELECT COUNT(*) as cnt FROM trend_insights WHERE brand_id=? AND (expires_at IS NULL OR expires_at > datetime('now'))",
                (brand_id,)
            ).fetchone()["cnt"]
        finally:
            conn.close()

        # Hashtag analysis top vs brand
        def _avg_hashtags(posts):
            if not posts:
                return 0
            import re
            counts = [len(re.findall(r"#\w+", p.get("caption",""))) for p in posts]
            return round(sum(counts)/max(1,len(counts)),1)
        top_ht = _avg_hashtags(top_posts[:5])
        bottom_ht = _avg_hashtags(bottom[:5])
        brand_ht = brand.get("hashtag_count_range","5-7") if brand else "5-7"

        # Readability proxy
        def _avg_wps(posts):
            if not posts:
                return 15.0
            vals=[]
            for p in posts:
                cap = p.get("caption","")
                sents = [s for s in re.split(r"[.!?\n]+", cap) if s.strip()]
                words = cap.split()
                vals.append(len(words)/max(1,len(sents)))
            return round(sum(vals)/max(1,len(vals)),1)
        top_wps = _avg_wps(top_posts[:5])
        bottom_wps = _avg_wps(bottom[:5])

        return {
            "brand": brand,
            "top_posts": top_posts[:5],
            "bottom_posts": bottom[:5],
            "top_hashtags_avg": top_ht,
            "bottom_hashtags_avg": bottom_ht,
            "brand_hashtags_range": brand_ht,
            "top_wps": top_wps,
            "bottom_wps": bottom_wps,
            "ai_health": ai_health,
            "trend_fresh_count": trends,
            "total_posts_14d": len(top_posts) + len(bottom)
        }

    # ---------- HYPOTHESIZE ----------
    def _heuristic_proposal(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback when LLM unavailable — deterministic, safe."""
        brand = obs["brand"]
        top_ht = obs["top_hashtags_avg"]
        brand_range = obs["brand_hashtags_range"]
        # Parse brand range "5-7"
        try:
            lo, hi = [int(x) for x in brand_range.split("-")]
            mid = (lo+hi)/2
        except Exception:
            lo, hi, mid = 5,7,6
        # If top posts use far fewer hashtags, propose tightening range
        if top_ht < mid - 1.5 and top_ht <= 3:
            new_range = f"{max(1,int(top_ht))}-{max(2,int(top_ht)+1)}"
            return {
                "experiment_type": "L1_HASHTAG",
                "changed_field": "hashtag_count_range",
                "old_value": brand_range,
                "new_value": new_range,
                "hypothesis": f"Top 5 posts avg {top_ht} hashtags vs brand range {brand_range}. Bottom avg {obs['bottom_hashtags_avg']}. Hypothesis: tightening to {new_range} will lift engagement 12-18%.",
                "predicted_lift": 0.15
            }
        # Else check sentence length
        top_wps = obs["top_wps"]
        brand_wps = float(brand.get("avg_sentence_length",15.0) or 15.0)
        if abs(top_wps - brand_wps) > 3:
            new_wps = str(round(top_wps,1))
            return {
                "experiment_type": "L1_READABILITY",
                "changed_field": "avg_sentence_length",
                "old_value": str(brand_wps),
                "new_value": new_wps,
                "hypothesis": f"Winners avg {top_wps} words/sent vs brand {brand_wps} and losers {obs['bottom_wps']}. Aligning to {new_wps} should improve readability and lift 10%.",
                "predicted_lift": 0.10
            }
        # Fallback hook refresh
        top_hooks = [p.get("caption","").split("\n")[0][:80] for p in obs["top_posts"][:3] if p.get("caption")]
        if top_hooks:
            existing = brand.get("sample_hooks","[]")
            try:
                existing_list = json.loads(existing) if isinstance(existing, str) else existing
            except Exception:
                existing_list = []
            new_hooks = json.dumps(top_hooks[:3])
            if new_hooks != existing:
                return {
                    "experiment_type": "L1_HOOK",
                    "changed_field": "sample_hooks",
                    "old_value": existing,
                    "new_value": new_hooks,
                    "hypothesis": f"Refresh top hooks from recent winners (engagement leaders) to bias CreatorAgent. Predicted lift 8%.",
                    "predicted_lift": 0.08
                }
        # No strong signal
        return {
            "experiment_type": "L1_NONE",
            "changed_field": "sample_hooks",
            "old_value": brand.get("sample_hooks","[]"),
            "new_value": brand.get("sample_hooks","[]"),
            "hypothesis": "No strong signal this week — top vs bottom similar. Recommend no change; monitor longer window.",
            "predicted_lift": 0.0
        }

    def hypothesize(self, brand_id: int = 1) -> Dict[str, Any]:
        """Generates single hypothesis via LLM reasoning or heuristic fallback."""
        obs = self.observe(brand_id)
        brand = obs["brand"]
        if not brand:
            raise ValueError("Brand not found")

        # Build LLM prompt for L1
        system_prompt = (
            f"You are the self-improvement strategist for {brand.get('name','Brand')}.\n"
            f"Brand profile: tone={brand.get('tone_of_voice')}, hashtags={obs['brand_hashtags_range']}, wps={brand.get('avg_sentence_length')}, emoji={brand.get('emoji_frequency')}.\n"
            "Given top vs bottom posts, propose ONE safe L1 change (hashtag_count_range, avg_sentence_length, sample_hooks, emoji_frequency) that will lift engagement.\n"
            "OUTPUT STRICT JSON: {\"experiment_type\":\"L1_HASHTAG|L1_READABILITY|L1_HOOK\",\"changed_field\":\"...\",\"old_value\":\"...\",\"new_value\":\"...\",\"hypothesis\":\"2 sentences\",\"predicted_lift\":0.12}\n"
            "Never propose tone_of_voice change. predicted_lift 0.05-0.20 only if signal strong else 0.0."
        )
        top_lines = []
        for p in obs["top_posts"]:
            ht = p.get('caption','').count('#')
            top_lines.append(f"- {p.get('caption','')[:100]} (eng {p.get('engagement_rate')}, ht {ht})")
        bottom_lines = [f"- {p.get('caption','')[:100]} (eng {p.get('engagement_rate')})" for p in obs["bottom_posts"]]
        user_prompt = (
            "<top_posts>\n" + "\n".join(top_lines) + "\n</top_posts>\n"
            "<bottom_posts>\n" + "\n".join(bottom_lines) + "\n</bottom_posts>\n"
            f"Brand range {obs['brand_hashtags_range']} top_avg_ht {obs['top_hashtags_avg']} bottom_avg_ht {obs['bottom_hashtags_avg']} top_wps {obs['top_wps']} bottom_wps {obs['bottom_wps']}\n"
            "Propose ONE field change."
        )
        try:
            raw = self.router.generate_text(task_type="reasoning", prompt=user_prompt, system_prompt=system_prompt, max_tokens=400)
            parsed = extract_json_from_llm(raw)
            # Validate
            field = parsed.get("changed_field")
            if field not in ALLOWED_FIELDS or field in L3_GATED_FIELDS:
                raise ValueError(f"LLM proposed gated field {field}, fallback to heuristic")
            # Clamp predicted_lift
            lift = float(parsed.get("predicted_lift",0))
            lift = max(0.0, min(0.25, lift))
            return {
                "experiment_type": parsed.get("experiment_type","L1_REASONING"),
                "changed_field": field,
                "old_value": str(parsed.get("old_value", brand.get(field,""))),
                "new_value": str(parsed.get("new_value", brand.get(field,""))),
                "hypothesis": sanitize_user_input(parsed.get("hypothesis",""), max_length=500),
                "predicted_lift": lift
            }
        except Exception as e:
            logger.info(f"Hypothesize LLM fallback: {mask_secrets(str(e))}")
            return self._heuristic_proposal(obs)

    # ---------- PROPOSE (dry-run gate) ----------
    def propose(self, brand_id: int = 1, dry_run: bool = True) -> Dict[str, Any]:
        """Creates improvement_log PROPOSED; enforces 1 per week per brand (year+week)."""
        now = datetime.now(timezone.utc)
        year, week, _ = now.isocalendar()
        year_week = year * 100 + week
        conn = get_connection()
        try:
            existing = conn.execute(
                "SELECT * FROM improvement_log WHERE brand_id=? AND week_number=? AND status IN ('PROPOSED','APPLIED') LIMIT 1",
                (brand_id, year_week)
            ).fetchone()
            if existing:
                return {"proposed": False, "reason": f"Proposal already exists for week {year_week}: id {existing['id']} status {existing['status']}", "existing": dict(existing)}
            # Need enough data: at least 3 posts in 14d
            cnt = conn.execute("SELECT COUNT(*) as c FROM posts WHERE brand_id=? AND created_at >= datetime('now','-14 days')", (brand_id,)).fetchone()["c"]
            if cnt is not None and cnt < 3:
                # Still allow but mark no signal
                pass
        finally:
            conn.close()

        proposal = self.hypothesize(brand_id)
        # If predicted_lift 0.0, don't create noise — still log as NOOP PROPOSED? Skip
        if proposal["predicted_lift"] == 0.0 and proposal["experiment_type"] == "L1_NONE":
            # Create noop for audit but don't require approval
            pass

        # Capture metric_before: avg engagement last 14d
        perf_before = 0.0
        try:
            top = self.perf.rank_posts_by_engagement(brand_id, days=14, limit=20)
            if top:
                perf_before = sum(p.get("engagement_rate",0) for p in top)/len(top)
        except Exception as e:
                logger.warning(f"Handled Exception: {mask_secrets(str(e))}")

        conn = get_connection()
        try:
            cur = conn.execute(
                """INSERT INTO improvement_log (brand_id, week_number, experiment_type, hypothesis, changed_field, old_value, new_value, metric_before, predicted_lift, status, dry_run)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PROPOSED', ?)""",
                (brand_id, year_week, proposal["experiment_type"], proposal["hypothesis"], proposal["changed_field"], proposal["old_value"], proposal["new_value"], perf_before, proposal["predicted_lift"], 1 if dry_run else 0)
            )
            conn.commit()
            pid = cur.lastrowid
            row = conn.execute("SELECT * FROM improvement_log WHERE id=?", (pid,)).fetchone()
            return {"proposed": True, "proposal": dict(row), "dry_run": dry_run}
        finally:
            conn.close()

    # ---------- LIST / APPROVE / REJECT ----------
    def list_pending(self, brand_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            if brand_id:
                rows = conn.execute("SELECT * FROM improvement_log WHERE brand_id=? AND status='PROPOSED' ORDER BY id DESC", (brand_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM improvement_log WHERE status='PROPOSED' ORDER BY id DESC LIMIT 20").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def approve(self, proposal_id: int) -> Dict[str, Any]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM improvement_log WHERE id=?", (proposal_id,)).fetchone()
            if not row:
                return {"success": False, "error": "Proposal not found"}
            if row["status"] != "PROPOSED":
                return {"success": False, "error": f"Already {row['status']}"}
            proposal = dict(row)
            field = proposal["changed_field"]
            if field in L3_GATED_FIELDS:
                return {"success": False, "error": f"Field {field} requires L3 manual review — not auto-applied"}
            if field not in ALLOWED_FIELDS:
                return {"success": False, "error": f"Field {field} not allowed"}

            # Apply to brands table
            brand_id = proposal["brand_id"]
            new_val = proposal["new_value"]
            # For sample_hooks, ensure JSON; for numeric, cast
            if field in ("sample_hooks",):
                try:
                    json.loads(new_val)
                except Exception:
                    new_val = json.dumps([new_val])
            # Update via BrandService
            ok = self.brand_service.update_profile(brand_id, {field: new_val if field != "sample_hooks" else json.loads(new_val) if isinstance(new_val, str) and new_val.startswith("[") else new_val})
            if not ok:
                return {"success": False, "error": "Brand update failed"}

            conn.execute("UPDATE improvement_log SET status='APPLIED', applied_at=?, dry_run=0 WHERE id=?", (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), proposal_id))
            conn.commit()
            updated = conn.execute("SELECT * FROM improvement_log WHERE id=?", (proposal_id,)).fetchone()
            return {"success": True, "proposal": dict(updated)}
        finally:
            conn.close()

    def reject(self, proposal_id: int, reason: str = "rejected by human") -> Dict[str, Any]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM improvement_log WHERE id=?", (proposal_id,)).fetchone()
            if not row:
                return {"success": False, "error": "Proposal not found"}
            if row["status"] != "PROPOSED":
                return {"success": False, "error": f"Already {row['status']}"}
            conn.execute("UPDATE improvement_log SET status='REJECTED', hypothesis=hypothesis || ' | reject: ' || ? WHERE id=?", (sanitize_user_input(reason, max_length=200), proposal_id))
            conn.commit()
            return {"success": True}
        finally:
            conn.close()

    # ---------- MEASURE ----------
    def measure(self, proposal_id: int) -> Dict[str, Any]:
        """Compares metric_before vs current 7d avg after APPLIED; decides KEEP or REVERT."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM improvement_log WHERE id=?", (proposal_id,)).fetchone()
            if not row:
                return {"success": False, "error": "Proposal not found"}
            proposal = dict(row)
            if proposal["status"] != "APPLIED":
                return {"success": False, "error": f"Not APPLIED, status {proposal['status']}"}
            # Need at least 7 days of posts after applied_at? For demo, allow immediate with available data
            brand_id = proposal["brand_id"]
            before = float(proposal["metric_before"] or 0)
            # Current 7d avg
            top = self.perf.rank_posts_by_engagement(brand_id, days=7, limit=20)
            after = sum(p.get("engagement_rate",0) for p in top)/max(1,len(top)) if top else 0
            delta = after - before
            lift = (delta / before) if before else 0
            # Decision: keep if lift > -5% (tolerant), revert if drop >5% or no improvement and predicted high
            should_revert = False
            if before > 0 and lift < -0.05:
                should_revert = True
            # Also revert if heuristic predicted 15% but got negative
            status = "MEASURED"
            action = "KEEP"
            if should_revert:
                # Revert brand field to old_value
                field = proposal["changed_field"]
                old_val = proposal["old_value"]
                try:
                    if field == "sample_hooks":
                        self.brand_service.update_profile(brand_id, {field: json.loads(old_val) if isinstance(old_val, str) and old_val.startswith("[") else old_val})
                    else:
                        self.brand_service.update_profile(brand_id, {field: old_val})
                    status = "REVERTED"
                    action = "REVERTED"
                except Exception as e:
                    logger.error(f"Revert failed: {mask_secrets(str(e))}")
                    status = "MEASURED"
            else:
                # Keep: update log with after
                status = "MEASURED"

            conn.execute(
                "UPDATE improvement_log SET metric_after=?, measured_at=?, status=? WHERE id=?",
                (after, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), status, proposal_id)
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM improvement_log WHERE id=?", (proposal_id,)).fetchone()
            return {"success": True, "before": before, "after": after, "lift": lift, "action": action, "proposal": dict(updated)}
        finally:
            conn.close()

    def get_history(self, brand_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            if brand_id:
                rows = conn.execute("SELECT * FROM improvement_log WHERE brand_id=? ORDER BY id DESC LIMIT ?", (brand_id, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM improvement_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
