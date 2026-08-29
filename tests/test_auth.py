import pytest
from httpx import ASGITransport, AsyncClient, Response
import respx

from app.main import app
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.models import Client, ApiKey
from app.core.security import generate_api_key, hash_api_key


@pytest.fixture(autouse=True)
def setup_db():
    # fresh schema per test run, no leftover rows messing with assertions
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_test_client_with_key() -> str:
    db = SessionLocal()
    client = Client(name="Test Client", tier="free")
    db.add(client)
    db.flush()

    raw_key = generate_api_key()
    db.add(ApiKey(client_id=client.id, key_hash=hash_api_key(raw_key)))
    db.commit()
    db.close()
    return raw_key


@pytest.mark.asyncio
async def test_missing_auth_header_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "llama3.2:1b", "messages": []},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_garbage_key_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer totally_made_up_key"},
            json={"model": "llama3.2:1b", "messages": []},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_valid_key_accepted():
    raw_key = _create_test_client_with_key()

    respx.post(f"{settings.inference_base_url}/v1/chat/completions").mock(
        return_value=Response(200, json={
            "id": "chatcmpl-fake",
            "choices": [{"message": {"role": "assistant", "content": "hey"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        })
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={"model": "llama3.2:1b", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert resp.status_code == 200