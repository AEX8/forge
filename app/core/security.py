import hashlib
import secrets

API_KEY_PREFIX = "fk_live_"


def generate_api_key() -> str:
    # secrets.token_urlsafe is the "actually meant for this" choice here,
    # not random.choice or anything from the random module, that stuff
    # is predictable enough
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    # sha256 is fine, unlike passwords an api key is already high entropy random data, it doesn't need bcrypt's deliberate slowness
    return hashlib.sha256(raw_key.encode()).hexdigest()