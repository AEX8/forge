from sqlalchemy.orm import Session

from app.core.models import UsageLog


def log_usage(
    db: Session,
    api_key_id,
    status_code: int,
    model_used: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    latency_ms: int | None = None,
    flagged: bool = False,
    flagged_reason: str | None = None,
):
    # deliberately not raising if this fails, a logging hiccup should nver take down the actual response the client is waiting on
    try:
        entry = UsageLog(
            api_key_id=api_key_id,
            status_code=status_code,
            model_used=model_used,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            flagged=flagged,
            flagged_reason=flagged_reason,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()