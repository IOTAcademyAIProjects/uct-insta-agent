"""
Audit Telemetry — Structured logging for critical pipeline failure points (Phase 5)
Writes to structured logger and optionally to analytics_cache / improvement_log
"""

import logging
import json
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core.security import mask_secrets

logger = logging.getLogger("clawagent.audit")

# Structured audit logger setup
audit_logger = logging.getLogger("clawagent.audit")
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s AUDIT %(message)s')
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)

def audit(event: str, data: Dict[str, Any], level: str = "info", brand_id: Optional[int] = None):
    """Emits structured JSON audit log with masking."""
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4())[:8],
        "brand_id": brand_id,
        "data": {k: mask_secrets(str(v)) if isinstance(v, str) else v for k, v in data.items()}
    }
    msg = json.dumps(payload, ensure_ascii=False)
    if level == "error":
        audit_logger.error(msg)
        logger.error(msg)
    elif level == "warning":
        audit_logger.warning(msg)
        logger.warning(msg)
    else:
        audit_logger.info(msg)
        logger.info(msg)
    # Optionally persist to DB for leader audit (non-blocking)
    try:
        from db.repository import get_connection
        conn = get_connection()
        try:
            conn.execute("INSERT INTO analytics_cache (brand_id, period, summary, content_ranking) VALUES (?, ?, ?, ?)",
                         (brand_id or 1, event, msg[:2000], json.dumps(data)[:2000]))
            conn.commit()
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass
