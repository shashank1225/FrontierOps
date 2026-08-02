from time import perf_counter

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from observability.metrics import API_DURATION, API_REQUESTS


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            labels = {"method": request.method, "route": route_path}
            API_DURATION.labels(**labels).observe(perf_counter() - started_at)
            API_REQUESTS.labels(**labels, status_code=str(status_code)).inc()
