import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.metrics import HTTP_REQUESTS, HTTP_REQUEST_DURATION


class MetricsMiddleware:
    """
    Records request count and duration for every HTTP request.

    This is plain ASGI instead of BaseHTTPMiddleware on purpose. BaseHTTPMiddleware
    hands control back as soon as the headers are sent, so for a streaming response
    it would record the time to the first byte instead of the time until the
    stream actually finished.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # skip websockets/lifespan, and don't count Prometheus scraping itself
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status = 500  # stays 500 if the app crashes before sending a response

        async def send_with_status(message: Message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            # the router puts the matched route on the scope, which gives us the
            # path template instead of the raw URL. No match means a 404.
            route = scope.get("route")
            route_label = route.path if route else "unmatched"
            method = scope["method"]

            HTTP_REQUESTS.labels(method, route_label, str(status)).inc()
            HTTP_REQUEST_DURATION.labels(method, route_label).observe(
                time.perf_counter() - start
            )
