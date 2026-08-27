"""
ClawAgent FastAPI — Health & Ops Endpoints + Phase 5 Rate Limiting & Observability
SPEC_SHEET.md:759-851, PRODUCTION_PLAN_10_10.md Phase 5
"""

import os
import time
import uuid
import logging
from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from core.model_router import get_default_router
from db.repository import get_connection
from services.scheduler_service import SchedulerService
from services.brand_service import BrandService
from core.security import mask_secrets

# Structured logging setup
logger = logging.getLogger("clawagent.api")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

app = FastAPI(title="ClawAgent Internal API", version="3.2.0")

# Rate limiting via slowapi (Phase 5) — fallback to in-memory if not available
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded as SlowRateLimit
    from slowapi.middleware import SlowAPIMiddleware
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(SlowRateLimit, lambda r, e: JSONResponse(status_code=429, content={"detail": f"Rate limit exceeded: {e.detail}"}))
    app.add_middleware(SlowAPIMiddleware)
    SLOWAPI_ENABLED = True
except ImportError:
    limiter = None
    SLOWAPI_ENABLED = False
    logger.warning("slowapi not installed — API rate limiting disabled (install slowapi for prod)")

# Request ID middleware for observability
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    start = time.time()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    latency = int((time.time() - start) * 1000)
    logger.info(f"request_id={request_id} method={request.method} path={request.url.path} status={response.status_code} latency_ms={latency}")
    return response

def verify_bearer(authorization: Optional[str] = Header(None)):
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
    return {"status": "ok", "version": "3.2.0"}

@app.get("/api/v3/models/status")
def models_status():
    router = get_default_router()
    status = router.get_status()
    return {"providers": status}

@app.post("/api/v3/models/reload")
def models_reload(authorized: bool = Depends(verify_bearer)):
    router = get_default_router()
    try:
        from core.config_loader import ConfigLoader
        new_config = ConfigLoader.load_yaml(router.config_path)
        if not isinstance(new_config, dict) or "providers" not in new_config or "fallback_chains" not in new_config:
            raise ValueError("Invalid config: missing 'providers' or 'fallback_chains'")
        providers = set(new_config.get("providers", {}).keys())
        for task, chain in new_config.get("fallback_chains", {}).items():
            if not isinstance(chain, list):
                raise ValueError(f"fallback_chains[{task}] must be list")
            for p in chain:
                if p not in providers:
                    raise ValueError(f"fallback_chains[{task}] references unknown provider '{p}'")
        router._on_config_reloaded(new_config)
        status = router.get_status()
        active = sum(1 for v in status.values() if v.get("enabled") and v.get("has_credentials"))
        disabled = len(status) - active
        logger.info(f"models_reload success active={active} disabled={disabled}")
        return {"reloaded": True, "providers_active": active, "providers_disabled": disabled}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"models_reload failed: {mask_secrets(str(e))}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/brands")
def list_brands():
    bs = BrandService()
    return {"brands": bs.list_all()}

@app.get("/api/v3/intelligence/brief")
def get_brief(request: Request, brand_id: Optional[int] = None, force: bool = False):
    svc = SchedulerService()
    if force:
        from agents.research_agent import ResearchAgent
        ra = ResearchAgent()
        text = ra.generate_weekly_brief(brand_id=brand_id)
        return {"brief": text, "cached": False}
    res = svc.generate_weekly_brief_if_needed(brand_id=brand_id, force=False)
    return res

@app.get("/api/v3/intelligence/trends")
def get_trends(request: Request, brand_id: Optional[int] = None):
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
def self_improve_propose(request: Request, brand_id: Optional[int] = None, dry_run: bool = True, authorized: bool = Depends(verify_bearer)):
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

@app.get("/api/v3/health")
def api_health():
    conn = get_connection()
    try:
        conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception as e:
        logger.warning(f"health db check failed: {mask_secrets(str(e))}")
        db_ok = False
    finally:
        try:
            conn.close()
        except Exception as e:
            logger.warning(f"health conn close failed: {mask_secrets(str(e))}")
    router = get_default_router()
    status = router.get_status()
    healthy_providers = sum(1 for v in status.values() if v.get("circuit_state") == "CLOSED")
    return {"db": "ok" if db_ok else "fail", "providers_healthy": healthy_providers, "status": "ok" if db_ok else "degraded"}
