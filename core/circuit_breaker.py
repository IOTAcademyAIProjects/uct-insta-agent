"""
Thread-safe Circuit Breaker Implementation with Single-Probe Locking
"""

import time
import threading
from typing import Dict

class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout_seconds: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()
        self._probe_in_flight = False
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """
        Determines whether a request to this provider is permitted.
        In HALF_OPEN state, only ONE probe request is permitted at a time.
        """
        with self._lock:
            now = time.time()
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                if now - self.last_failure_time >= self.recovery_timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = now
                    self._probe_in_flight = True
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                # If a probe is already executing, block other requests until probe resolves
                if not self._probe_in_flight:
                    self._probe_in_flight = True
                    return True
                return False
            
            return False

    @property
    def is_open(self) -> bool:
        return not self.allow_request()

    def record_success(self):
        """Records a successful API call, closing the circuit if it was HALF_OPEN."""
        with self._lock:
            if self.state != CircuitState.CLOSED:
                self.state = CircuitState.CLOSED
                self.last_state_change = time.time()
            self.failure_count = 0
            self._probe_in_flight = False

    def record_failure(self):
        """Records a failure. If threshold is reached, opens the circuit."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self._probe_in_flight = False
            
            if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                if self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.OPEN
                    self.last_state_change = self.last_failure_time

    def get_status(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout_seconds": self.recovery_timeout_seconds,
                "probe_in_flight": self._probe_in_flight,
                "last_failure_time": self.last_failure_time
            }
