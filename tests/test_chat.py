import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.models import Client, ApiKey
from app.core.security import generate_api_key, hash_api_key


@pytest.fixture(autouse=True)
def setup_db():
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
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
@respx.mock
async def test_chat_completions_proxies_to_backend():
    raw_key = _create_test_client_with_key()

    fake_ollama_response = {
        "id": "chatcmpl-fake",
        "choices": [{"message": {"role": "assistant", "content": "Hi there"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }
    respx.post(f"{settings.inference_base_url}/v1/chat/completions").mock(
        return_value=Response(200, json=fake_ollama_response)
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={
                "model": "llama3.2:1b",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["content"] == "Hi there"
    assert "latency_ms" in body["forge_meta"]


@pytest.mark.asyncio
@respx.mock
async def test_chat_completions_surfaces_backend_errors():
    raw_key = _create_test_client_with_key()

    respx.post(f"{settings.inference_base_url}/v1/chat/completions").mock(
        return_value=Response(500, json={"error": "model not loaded"})
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={"model": "llama3.2:1b", "messages": []},
        )

    assert resp.status_code == 500