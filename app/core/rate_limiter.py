import time
from pathlib import Path

import redis

from app.core.config import settings

_redis_client = redis.from_url(settings.redis_url, decode_responses=True)
_script_path = Path(__file__).parent / "rate_limit.lua"
_token_bucket_script = _redis_client.register_script(_script_path.read_text())


def check_rate_limit(client_id: str, capacity: int = 20, refill_rate: float = 0.5) -> bool:
    """
    capacity: max requests a client can burst before waiting
    refill_rate: tokens regenerated per second (0.5 = 1 every 2 seconds)

    Returns True if this request is allowed, False if the client should get a 429.
    """
    key = f"rate_limit:{client_id}"
    allowed, _remaining = _token_bucket_script(
        keys=[key],
        args=[capacity, refill_rate, time.time()],
    )
    return bool(allowed)