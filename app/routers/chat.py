from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import httpx, time, json
from fastapi.responses import StreamingResponse


from app.core.inference import inference_client
from app.core.auth import get_current_client
from app.core.models import Client, ApiKey
from app.core.rate_limiter import check_rate_limit
from app.core.prompt_risk import assess_payload, RiskLevel
from app.core.usage import log_usage
from app.core.database import get_db, SessionLocal

router = APIRouter()

def _sse_error(message: str) -> str:
    # headers already left as 200, so the only way to go oops now is inside the stream
    return f"data: {json.dumps({'error': {'message': message}})}\n\n"

async def _stream_and_log(payload: dict, api_key_id, risk):
    """
    Passes sse lines straight through to the client, and quietly eavesdrops
    on the final chunk for token counts so metering still works.
    """
    start = time.perf_counter()
    tokens_in = None
    tokens_out = None
    status = 200

    try:
        async for line in inference_client.chat_completion_stream(payload):
            # sse events are separated by a blank line, aiter_lines ate ours
            yield f"{line}\n\n"

            if not line.startswith("data:"):
                continue
            body = line.removeprefix("data:").strip()
            if body == "[DONE]":
                continue
            try:
                usage = json.loads(body).get("usage")
            except json.JSONDecodeError:
                continue
            if usage:
                tokens_in = usage.get("prompt_tokens")
                tokens_out = usage.get("completion_tokens")
    except httpx.HTTPError:
        # headers are already sent by now, so all we can do is end the
        # stream with an error event and record that it went badly
        status = 502
        yield 'data: {"error": "inference backend failed mid stream"}\n\n'
    finally:
        # fresh session on purpose, the request scoped one may be closed
        # by the time a long stream finishes
        db = SessionLocal()
        try:
            log_usage(
                db, api_key_id, status_code=status,
                model_used=payload.get("model"),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=round((time.perf_counter() - start) * 1000),
                flagged=(risk.level == RiskLevel.MEDIUM),
                flagged_reason=risk.reason if risk.level == RiskLevel.MEDIUM else None,
            )
        finally:
            db.close()

@router.post("/v1/chat/completions")
async def chat_completions(
    payload: dict,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    # we need the api_key row not just the client, since usage_logs tracks per-key not per-client (a client could have multiple keys someday)
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
        return StreamingResponse(
            _stream_and_log(payload, api_key.id, risk),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

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