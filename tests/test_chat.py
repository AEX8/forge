import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_health():
    # just making sure the app boots
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
@respx.mock
async def test_chat_completions_proxies_to_backend():
    # pretending to be ollama so we don't need a real model loaded just to run tests
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
            json={
                "model": "llama3.2:1b",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["content"] == "Hi there"
    # making sure we actually tacked our latency field 
    assert "latency_ms" in body["forge_meta"]


@pytest.mark.asyncio
@respx.mock
async def test_chat_completions_surfaces_backend_errors():
    respx.post(f"{settings.inference_base_url}/v1/chat/completions").mock(
        return_value=Response(500, json={"error": "model not loaded"})
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/chat/completions",
            json={"model": "llama3.2:1b", "messages": []},
        )

    assert resp.status_code == 500