"""
Custom Exceptions for ClawAgent
"""

class ClawAgentException(Exception):
    """Base exception for ClawAgent."""
    pass

class AllProvidersExhausted(ClawAgentException):
    """Raised when all candidate providers for a given task fail or are unavailable."""
    pass

class CircuitBreakerOpen(ClawAgentException):
    """Raised when an operation is attempted on a provider with an OPEN circuit breaker."""
    pass

class ConfigReloadError(ClawAgentException):
    """Raised when parsing or applying config updates fails."""
    pass

class NoActiveInstagramConnection(ClawAgentException):
    """Raised when no active Instagram connection is found in Composio."""
    pass

class BrandNotFound(ClawAgentException):
    """Raised when a requested brand profile does not exist."""
    pass

class PlatformAdapterError(ClawAgentException):
    """Raised when a platform adapter fails during media prep or publishing."""
    pass

class RateLimitExceeded(ClawAgentException):
    """Raised when provider rate limits are reached."""
    pass
