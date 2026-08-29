import time

from fastapi import APIRouter, HTTPException
import httpx

from app.core.inference import inference_client

router = APIRouter()


@router.post("/v1/chat/completions")
async def chat_completions(payload: dict):
    """
    Milestone 1: prove the round trip works.
    Client -> Forge -> Ollama -> Llama -> Forge -> Client
    No auth, no rate limiting, no logging yet - those come in later branches.
    """
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