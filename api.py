"""
ClawAgent FastAPI — Health & Ops Endpoints
SPEC_SHEET.md:759-851
"""

import os
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from core.model_router import get_default_router
from db.repository import get_connection
from services.scheduler_service import SchedulerService
from services.brand_service import BrandService

app = FastAPI(title="ClawAgent Internal API", version="3.0.0")

def verify_bearer(authorization: Optional[str] = Header(None)):
    # Optional bearer for reload; allow if no token configured
    expected = os.getenv("API_BEARER_TOKEN")
    if not expected:
        return True
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1]
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid token")
    return True

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0"}

@app.get("/api/v3/models/status")
def models_status():
    router = get_default_router()
    status = router.get_status()
    # Enrich with circuit state
    return {"providers": status}

@app.post("/api/v3/models/reload")
def models_reload(authorized: bool = Depends(verify_bearer)):
    router = get_default_router()
    try:
        from core.config_loader import ConfigLoader
        new_config = ConfigLoader.load_yaml(router.config_path)
        # Validate before applying: must have providers and fallback_chains, each chain refs known providers
        if not isinstance(new_config, dict) or "providers" not in new_config or "fallback_chains" not in new_config:
            raise ValueError("Invalid config: missing 'providers' or 'fallback_chains'")
        providers = set(new_config.get("providers", {}).keys())
        for task, chain in new_config.get("fallback_chains", {}).items():
            if not isinstance(chain, list):
                raise ValueError(f"fallback_chains[{task}] must be list")
            for p in chain:
                if p not in providers:
                    raise ValueError(f"fallback_chains[{task}] references unknown provider '{p}'")
        # Keep old config on failure — only clear after validation passes
        router._on_config_reloaded(new_config)
        status = router.get_status()
        active = sum(1 for v in status.values() if v.get("enabled") and v.get("has_credentials"))
        disabled = len(status) - active
        return {"reloaded": True, "providers_active": active, "providers_disabled": disabled}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/brands")
def list_brands():
    bs = BrandService()
    return {"brands": bs.list_all()}

@app.get("/api/v3/intelligence/brief")
def get_brief(brand_id: Optional[int] = None, force: bool = False):
    svc = SchedulerService()
    # Use cache unless force
    if force:
        from agents.research_agent import ResearchAgent
        ra = ResearchAgent()
        text = ra.generate_weekly_brief(brand_id=brand_id)
        return {"brief": text, "cached": False}
    res = svc.generate_weekly_brief_if_needed(brand_id=brand_id, force=False)
    return res

@app.get("/api/v3/intelligence/trends")
def get_trends(brand_id: Optional[int] = None):
    from services.trend_service import TrendService
    ts = TrendService()
    trends = ts.get_latest_trends(brand_id=brand_id)
    return {"trends": trends}

@app.get("/api/v3/scheduler/due")
def scheduler_due():
    svc = SchedulerService()
    due = svc.list_queue()
    return {"scheduled": due, "count": len(due)}

# Self-Improving Loop API — PRD 3.13 / SPEC 9
@app.post("/api/v3/self-improve/propose")
def self_improve_propose(brand_id: Optional[int] = None, dry_run: bool = True, authorized: bool = Depends(verify_bearer)):
    from services.self_improvement_service import SelfImprovementService
    svc = SelfImprovementService()
    return svc.propose(brand_id=brand_id or 1, dry_run=dry_run)

@app.get("/api/v3/self-improve/pending")
def self_improve_pending(brand_id: Optional[int] = None):
    from services.self_improvement_service import SelfImprovementService
    svc = SelfImprovementService()
    return {"pending": svc.list_pending(brand_id=brand_id)}

@app.post("/api/v3/self-improve/{proposal_id}/approve")
def self_improve_approve(proposal_id: int, authorized: bool = Depends(verify_bearer)):
    from services.self_improvement_service import SelfImprovementService
    svc = SelfImprovementService()
    return svc.approve(proposal_id)

@app.post("/api/v3/self-improve/{proposal_id}/reject")
def self_improve_reject(proposal_id: int, authorized: bool = Depends(verify_bearer)):
    from services.self_improvement_service import SelfImprovementService
    svc = SelfImprovementService()
    return svc.reject(proposal_id)

@app.post("/api/v3/self-improve/{proposal_id}/measure")
def self_improve_measure(proposal_id: int, authorized: bool = Depends(verify_bearer)):
    from services.self_improvement_service import SelfImprovementService
    svc = SelfImprovementService()
    return svc.measure(proposal_id)

@app.get("/api/v3/self-improve/history")
def self_improve_history(brand_id: Optional[int] = None, limit: int = 20):
    from services.self_improvement_service import SelfImprovementService
    svc = SelfImprovementService()
    return {"history": svc.get_history(brand_id=brand_id, limit=limit)}

# For Docker healthcheck
@app.get("/api/v3/health")
def api_health():
    conn = get_connection()
    try:
        conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        try:
            conn.close()
        except Exception:
            pass
    router = get_default_router()
    status = router.get_status()
    healthy_providers = sum(1 for v in status.values() if v.get("circuit_state") == "CLOSED")
    return {"db": "ok" if db_ok else "fail", "providers_healthy": healthy_providers, "status": "ok" if db_ok else "degraded"}
