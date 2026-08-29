import sys

from app.core.database import SessionLocal
from app.core.models import Client, ApiKey
from app.core.security import generate_api_key, hash_api_key


def create_client(name: str, tier: str = "free"):
    db = SessionLocal()
    try:
        client = Client(name=name, tier=tier)
        db.add(client)
        db.flush()  # so client.id actually exists before we use it below

        raw_key = generate_api_key()
        api_key = ApiKey(client_id=client.id, key_hash=hash_api_key(raw_key))
        db.add(api_key)
        db.commit()

        print(f"Created client '{name}' (tier: {tier})")
        print(f"API key (save this now, it will not be shown again): {raw_key}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.create_client <client_name> [tier]")
        sys.exit(1)

    name = sys.argv[1]
    tier = sys.argv[2] if len(sys.argv) > 2 else "free"
    create_client(name, tier)