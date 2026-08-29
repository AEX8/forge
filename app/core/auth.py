from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import ApiKey
from app.core.security import hash_api_key


async def get_current_client(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed API key")

    raw_key = authorization.removeprefix("Bearer ")
    key_hash = hash_api_key(raw_key)

    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        .first()
    )

    if not api_key:
        # deliberately the same generic message whether the key is wrong,
        # revoked, or just doesn't exist, no free hints for anyone probing
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key.client