import json

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.models import Client, ApiKey, UsageLog
from app.core.security import generate_api_key, hash_api_key

# what ollama's openai endpoint actually sends back, give or take some fields
SSE_BODY = (
    'data: {"choices":[{"delta":{"role":"assistant","content":"Hi"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":" there"}}]}\n\n'
    'data: {"choices":[],"usage":{"prompt_tokens":5,"completion_tokens":2}}\n\n'
    "data: [DONE]\n\n"
)


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


async def _stream_request(raw_key: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            "/v1/chat/completions",
            headers={"Authorization": f"Bearer {raw_key}"},
            json={
                "model": "llama3.2:1b",
                "stream": True,
                "messages": [{"role": "user", "content": "hello"}],
            },
        )


@pytest.mark.asyncio
@respx.mock
async def test_stream_passes_sse_through():
    raw_key = _create_test_client_with_key()
    route = respx.post(f"{settings.inference_base_url}/v1/chat/completions").mock(
        return_value=Response(200, text=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    resp = await _stream_request(raw_key)

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert '"content":" there"' in resp.text
    assert resp.text.rstrip().endswith("data: [DONE]")

    sent = json.loads(route.calls.last.request.content)
    assert sent["stream_options"] == {"include_usage": True}


@pytest.mark.asyncio
@respx.mock
async def test_stream_logs_token_usage():
    raw_key = _create_test_client_with_key()
    respx.post(f"{settings.inference_base_url}/v1/chat/completions").mock(
        return_value=Response(200, text=SSE_BODY, headers={"content-type": "text/event-stream"})
    )

    await _stream_request(raw_key)

    db = SessionLocal()
    logs = db.query(UsageLog).all()
    db.close()

    assert len(logs) == 1
    assert logs[0].status_code == 200
    assert logs[0].tokens_in == 5
    assert logs[0].tokens_out == 2


@pytest.mark.asyncio
@respx.mock
async def test_stream_backend_error_is_sent_in_band_and_logged():
    raw_key = _create_test_client_with_key()
    respx.post(f"{settings.inference_base_url}/v1/chat/completions").mock(
        return_value=Response(500, json={"error": "model not loaded"})
    )

    resp = await _stream_request(raw_key)

    assert resp.status_code == 200 
    assert "model not loaded" in resp.text

    db = SessionLocal()
    logs = db.query(UsageLog).all()
    db.close()

    assert len(logs) == 1
    assert logs[0].status_code == 500