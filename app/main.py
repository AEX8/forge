from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.metrics_middleware import MetricsMiddleware
from app.routers import chat

app = FastAPI(
    title="Forge",
    description="Self-hosted, OpenAI-compatible LLM gateway",
    version="0.1.0",
)

app.add_middleware(MetricsMiddleware)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    # Prometheus scrapes this, in its plain text exposition format
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
