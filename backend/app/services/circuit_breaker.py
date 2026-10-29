import time
import asyncio
from typing import Callable, Any
from fastapi import HTTPException


class CircuitBreakerOpenException(HTTPException):
    def __init__(self, service_name: str, retry_after: int):
        super().__init__(
            status_code=503,
            detail=f"{service_name} xizmati vaqtincha band yoki javob bermayapti (Circuit Breaker ochiq). Iltimos, {retry_after} soniyadan so'ng qayta urinib ko'ring.",
        )


class CircuitBreaker:
    """
    Circuit Breaker pattern to protect against cascading service failures.
    States: CLOSED (normal), OPEN (blocking requests), HALF_OPEN (probing).
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        call_timeout: float = 10.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.call_timeout = call_timeout

        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_state_change = time.time()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        now = time.time()

        # Check if we should transition from OPEN to HALF_OPEN
        if self.state == "OPEN":
            if now - self.last_state_change > self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.last_state_change = now
            else:
                retry_after = int(self.recovery_timeout - (now - self.last_state_change))
                raise CircuitBreakerOpenException(self.name, max(1, retry_after))

        try:
            # Wrap execution with strict timeout
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.call_timeout)

            # Success resets circuit
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                self.last_state_change = now
            elif self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)

            return result

        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = now

            if isinstance(e, asyncio.TimeoutError):
                raise HTTPException(
                    status_code=504,
                    detail=f"{self.name} chaqiruvi belgilangan {self.call_timeout}s vaqt ichida javob bermadi (Gateway Timeout).",
                )
            raise e


# Global Circuit Breakers for subsystems
docker_circuit_breaker = CircuitBreaker("Docker Engine API", failure_threshold=4, recovery_timeout=20.0, call_timeout=15.0)
github_circuit_breaker = CircuitBreaker("GitHub Public API", failure_threshold=5, recovery_timeout=45.0, call_timeout=8.0)
redis_circuit_breaker = CircuitBreaker("Redis Cache & Queue", failure_threshold=3, recovery_timeout=15.0, call_timeout=3.0)
