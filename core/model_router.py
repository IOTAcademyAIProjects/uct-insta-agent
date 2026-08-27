"""
Task-Based Model Router with Hot-Reload, Circuit Breakers, and Secret Masking
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List

from core.exceptions import AllProvidersExhausted
from core.circuit_breaker import CircuitBreaker
from core.config_loader import ConfigLoader, ConfigWatcher
from core.security import mask_secrets, validate_safe_url
from providers.base import ProviderClient
from providers.openai_compatible import OpenAICompatibleProvider
from providers.google_genai import GoogleGenAIProvider
from providers.pollinations import PollinationsProvider
from providers.replicate_provider import ReplicateProvider
from providers.banana_provider import BananaProvider

logger = logging.getLogger("clawagent.router")

class ModelRouter:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(project_root, "config", "models.yaml")
        
        self.config_path = config_path
        self.config = ConfigLoader.load_yaml(self.config_path)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.provider_instances: Dict[str, ProviderClient] = {}
        
        self._init_providers()
        
        # Start hot-reload watcher if configured
        if self.config.get("hot_reload", True):
            self.watcher = ConfigWatcher(self.config_path, self._on_config_reloaded)
        else:
            self.watcher = None

    def _init_providers(self):
        providers_conf = self.config.get("providers", {})
        for name, p_conf in providers_conf.items():
            if name not in self.circuit_breakers:
                cb_conf = p_conf.get("circuit_breaker", {})
                thresh = cb_conf.get("failure_threshold", 3)
                rec = cb_conf.get("recovery_timeout_seconds", 60)
                self.circuit_breakers[name] = CircuitBreaker(name, thresh, rec)

    def _on_config_reloaded(self, new_config: Dict[str, Any]):
        logger.info("Applying newly reloaded models.yaml configuration...")
        self.config = new_config
        self._init_providers()
        self.provider_instances.clear()

    def _get_provider_client(self, name: str) -> Optional[ProviderClient]:
        if name in self.provider_instances:
            return self.provider_instances[name]
        
        p_conf = self.config.get("providers", {}).get(name)
        if not p_conf:
            return None
        
        p_type = p_conf.get("type")
        client: Optional[ProviderClient] = None
        
        if p_type == "openai_compatible":
            client = OpenAICompatibleProvider(name, p_conf)
        elif p_type == "google_genai":
            client = GoogleGenAIProvider(name, p_conf)
        elif p_type == "pollinations":
            client = PollinationsProvider(name, p_conf)
        elif p_type == "replicate":
            client = ReplicateProvider(name, p_conf)
        elif p_type == "banana":
            client = BananaProvider(name, p_conf)
        
        if client:
            self.provider_instances[name] = client
        return client

    def _has_credentials(self, provider_name: str, p_conf: Dict[str, Any]) -> bool:
        p_type = p_conf.get("type")
        if p_type in ("pollinations", "ollama"):
            return True
        # Ollama uses type openai_compatible with localhost base_url and placeholder env
        base_url = str(p_conf.get("base_url", "")).lower()
        api_key_env = p_conf.get("api_key_env", "")
        if "localhost" in base_url or "127.0.0.1" in base_url or api_key_env == "OLLAMA_PLACEHOLDER":
            return True
        
        if not api_key_env:
            return True
        
        val = os.getenv(api_key_env, "").strip()
        return bool(val)

    def get_fallback_chain(self, task_type: str) -> List[str]:
        chains = self.config.get("fallback_chains", {})
        return chains.get(task_type, [])

    def route(self, task_type: str) -> ProviderClient:
        chain = self.get_fallback_chain(task_type)
        if not chain:
            default_p = self.config.get("defaults", {}).get(task_type)
            if default_p:
                chain = [default_p]

        providers_conf = self.config.get("providers", {})
        
        for p_name in chain:
            p_conf = providers_conf.get(p_name)
            if not p_conf or not p_conf.get("enabled", True):
                continue
            
            cb = self.circuit_breakers.get(p_name)
            if cb and cb.is_open:
                logger.warning(f"Skipping provider {p_name} for task {task_type}: Circuit breaker OPEN")
                continue
            
            if not self._has_credentials(p_name, p_conf):
                continue
            
            client = self._get_provider_client(p_name)
            if client:
                return client
                
        raise AllProvidersExhausted(f"No active, healthy providers available for task type: '{task_type}'")

    def generate_text(
        self,
        task_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 400,
        temperature: float = 0.7
    ) -> str:
        chain = self.get_fallback_chain(task_type)
        if not chain:
            default_p = self.config.get("defaults", {}).get(task_type)
            if default_p:
                chain = [default_p]
                
        providers_conf = self.config.get("providers", {})
        last_error = None
        
        for p_name in chain:
            p_conf = providers_conf.get(p_name)
            if not p_conf or not p_conf.get("enabled", True):
                continue
            
            cb = self.circuit_breakers.get(p_name)
            if cb and cb.is_open:
                continue
            
            if not self._has_credentials(p_name, p_conf):
                continue
            
            client = self._get_provider_client(p_name)
            if not client:
                continue
            
            try:
                start_t = time.time()
                result = client.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                latency = int((time.time() - start_t) * 1000)
                if cb:
                    cb.record_success()
                
                self._log_call(p_name, p_conf.get("model", ""), task_type, success=True, latency_ms=latency)
                return result
            except Exception as e:
                masked_err = mask_secrets(str(e))
                logger.error(f"Provider {p_name} failed for task {task_type}: {masked_err}")
                if cb:
                    cb.record_failure()
                self._log_call(p_name, p_conf.get("model", ""), task_type, success=False, error_msg=masked_err)
                last_error = masked_err
                continue
        
        raise AllProvidersExhausted(f"All providers exhausted for task '{task_type}'. Last error: {last_error}")

    def describe_image(self, image_url: str, prompt: Optional[str] = None, max_tokens: int = 150) -> str:
        # Validate URL to prevent SSRF in vision providers
        safe_url = validate_safe_url(image_url)
        chain = self.get_fallback_chain("vision")
        providers_conf = self.config.get("providers", {})
        last_error = None
        
        for p_name in chain:
            p_conf = providers_conf.get(p_name)
            if not p_conf or not p_conf.get("enabled", True):
                continue
            cb = self.circuit_breakers.get(p_name)
            if cb and cb.is_open:
                continue
            if not self._has_credentials(p_name, p_conf):
                continue
            
            client = self._get_provider_client(p_name)
            if not client or not client.supports_vision:
                continue
            
            try:
                start_t = time.time()
                desc = client.describe_image(safe_url, prompt=prompt, max_tokens=max_tokens)
                if cb:
                    cb.record_success()
                self._log_call(p_name, p_conf.get("model", ""), "vision", success=True, latency_ms=int((time.time()-start_t)*1000))
                return desc
            except Exception as e:
                masked_err = mask_secrets(str(e))
                logger.error(f"Vision provider {p_name} failed: {masked_err}")
                if cb:
                    cb.record_failure()
                self._log_call(p_name, p_conf.get("model", ""), "vision", success=False, error_msg=masked_err)
                last_error = masked_err
                continue
                
        raise AllProvidersExhausted(f"All vision providers failed. Last error: {last_error}")

    def generate_image(self, prompt: str, width: int = 1080, height: int = 1080, model: Optional[str] = None) -> bytes:
        chain = self.get_fallback_chain("image_generation")
        providers_conf = self.config.get("providers", {})
        last_error = None
        
        for p_name in chain:
            p_conf = providers_conf.get(p_name)
            if not p_conf or not p_conf.get("enabled", True):
                continue
            cb = self.circuit_breakers.get(p_name)
            if cb and cb.is_open:
                continue
            if not self._has_credentials(p_name, p_conf):
                continue
                
            client = self._get_provider_client(p_name)
            if not client:
                continue
                
            try:
                img_bytes = client.generate_image(prompt, width, height, model)
                if cb:
                    cb.record_success()
                return img_bytes
            except Exception as e:
                masked_err = mask_secrets(str(e))
                logger.error(f"Image gen provider {p_name} failed: {masked_err}")
                if cb:
                    cb.record_failure()
                last_error = masked_err
                continue
                
        raise AllProvidersExhausted(f"All image providers failed. Last error: {last_error}")

    def _log_call(self, provider: str, model: str, task_type: str, success: bool, latency_ms: int = 0, error_msg: Optional[str] = None):
        try:
            from db.repository import log_ai_call
            log_ai_call(provider, model, task_type, success, latency_ms=latency_ms, error_message=mask_secrets(error_msg))
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        status = {}
        providers_conf = self.config.get("providers", {})
        for name, p_conf in providers_conf.items():
            cb = self.circuit_breakers.get(name)
            has_creds = self._has_credentials(name, p_conf)
            status[name] = {
                "enabled": p_conf.get("enabled", True),
                "has_credentials": has_creds,
                "cost_tier": p_conf.get("cost_tier", "free"),
                "model": p_conf.get("model"),
                "circuit_state": cb.state if cb else "UNKNOWN",
                "failure_count": cb.failure_count if cb else 0
            }
        return status

_GLOBAL_ROUTER: Optional[ModelRouter] = None

def get_default_router() -> ModelRouter:
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = ModelRouter()
    return _GLOBAL_ROUTER
