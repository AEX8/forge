from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import httpx, time
from fastapi.responses import StreamingResponse

from app.core.inference import inference_client
from app.core.auth import get_current_client
from app.core.models import Client, ApiKey
from app.core.rate_limiter import check_rate_limit
from app.core.prompt_risk import assess_payload, RiskLevel
from app.core.usage import log_usage
from app.core.database import get_db

router = APIRouter()

async def _stream_and_log(payload: dict, db: Session, api_key_id, risk):
    """
    Streams chunks straight through to the client as they arrive, then logs
    usage once Ollama sends its final chunk (the one with "done": true, which
    carries the token counts, same info the non-streaming path gets upfront).
    """
    start = time.perf_counter()
    tokens_in = None
    tokens_out = None

    try:
        async for chunk in inference_client.chat_completion_stream(payload):
            yield chunk
            # ollama's final ndjson line includes usage stats once done=true, cheap enough to just try parsing every chunk for it
            try:
                data = json.loads(chunk)
                if data.get("done"):
                    tokens_in = data.get("prompt_eval_count")
                    tokens_out = data.get("eval_count")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # not every chunk is guaranteed clean single-line json, that's fine
    finally:
        latency_ms = round((time.perf_counter() - start) * 1000)
        log_usage(
            db, api_key_id, status_code=200,
            model_used=payload.get("model"),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            flagged=(risk.level == RiskLevel.MEDIUM),
            flagged_reason=risk.reason if risk.level == RiskLevel.MEDIUM else None,
        )


@router.post("/v1/chat/completions")
async def chat_completions(
    payload: dict,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    # we need the api_key row, not just the client, since usage_logs tracks per-key not per-client (a client could have multiple keys someday)
    api_key = client.api_keys[0]

    if not check_rate_limit(str(client.id)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, slow down a little")

    risk = assess_payload(payload)
    if risk.level == RiskLevel.HIGH:
        log_usage(
            db, api_key.id, status_code=400,
            flagged=True, flagged_reason=risk.reason,
        )
        raise HTTPException(status_code=400, detail=f"Request blocked: {risk.reason}")

    if payload.get("stream"):
        return StreamingResponse(_stream_and_log(payload, db, api_key.id, risk), media_type="application/x-ndjson",)

    start = time.perf_counter()

    try:
        result = await inference_client.chat_completion(payload)
    except httpx.HTTPStatusError as exc:
        log_usage(db, api_key.id, status_code=exc.response.status_code)
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Inference backend error: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        log_usage(db, api_key.id, status_code=502)
        raise HTTPException(status_code=502, detail=f"Could not reach inference backend: {exc}")

    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    result.setdefault("forge_meta", {})["latency_ms"] = latency_ms

    usage = result.get("usage", {})
    log_usage(
        db, api_key.id, status_code=200,
        model_used=payload.get("model"),
        tokens_in=usage.get("prompt_tokens"),
        tokens_out=usage.get("completion_tokens"),
        latency_ms=int(latency_ms),
        flagged=(risk.level == RiskLevel.MEDIUM),
        flagged_reason=risk.reason if risk.level == RiskLevel.MEDIUM else None,
    )

    return result