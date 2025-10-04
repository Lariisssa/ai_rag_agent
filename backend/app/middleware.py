"""
Middleware for request handling, rate limiting, and error handling
"""
from __future__ import annotations
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
import structlog
from .config import settings
from .exceptions import AppException

log = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter based on IP address
    Production deployment should use Redis or similar
    """

    def __init__(self, app, requests_per_window: int = 100, window_seconds: int = 300):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.request_counts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Clean old entries
        now = time.time()
        self.request_counts[client_ip] = [
            timestamp
            for timestamp in self.request_counts[client_ip]
            if now - timestamp < self.window_seconds
        ]

        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.requests_per_window:
            log.warning("rate_limit_exceeded", client_ip=client_ip)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.requests_per_window} requests per {self.window_seconds} seconds",
                },
            )

        # Record this request
        self.request_counts[client_ip].append(now)

        # Process request
        response = await call_next(request)
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handler that catches unhandled exceptions
    and returns consistent JSON error responses
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except AppException as e:
            log.error(
                "app_exception",
                error=str(e),
                status_code=e.status_code,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=e.status_code, content={"error": e.message}
            )
        except Exception as e:
            import traceback
            log.error(
                "unhandled_exception",
                error=str(e),
                error_type=type(e).__name__,
                path=request.url.path,
                traceback=traceback.format_exc(),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "detail": str(e),  # Always show for debugging
                },
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all requests with timing information
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Log request
        log.info(
            "request_start",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        # Process request
        response = await call_next(request)

        # Log response with timing
        duration = time.time() - start_time
        log.info(
            "request_complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        return response
