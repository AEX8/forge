from fastapi import APIRouter, HTTPException, Depends
import httpx
import time
from app.core.inference import inference_client
from app.core.auth import get_current_client
from app.core.models import Client
from app.core.rate_limiter import check_rate_limit

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(payload: dict, client: Client = Depends(get_current_client)):
    if not check_rate_limit(str(client.id)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded, slow down a little",
        )

    start = time.perf_counter()

    try:
        result = await inference_client.chat_completion(payload)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Inference backend error: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach inference backend: {exc}",
        )

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    result.setdefault("forge_meta", {})["latency_ms"] = latency_ms
    return result