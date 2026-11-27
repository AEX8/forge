import pytest
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY

from app.main import app


# The registry is global and lives for the whole test run, so these tests
# compare before and after values instead of expecting exact totals.
def _requests_count(method: str, route: str, status: str) -> float:
    value = REGISTRY.get_sample_value(
        "forge_http_requests_total",
        {"method": method, "route": route, "status": status},
    )
    return value or 0.0


async def _get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_format():
    resp = await _get("/metrics")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "forge_http_requests_total" in resp.text


@pytest.mark.asyncio
async def test_request_is_counted_by_route_template():
    before = _requests_count("GET", "/health", "200")

    await _get("/health")

    assert _requests_count("GET", "/health", "200") == before + 1


@pytest.mark.asyncio
async def test_unknown_path_is_counted_as_unmatched():
    before = _requests_count("GET", "unmatched", "404")

    resp = await _get("/definitely/not/a/route")

    assert resp.status_code == 404
    assert _requests_count("GET", "unmatched", "404") == before + 1


@pytest.mark.asyncio
async def test_metrics_scrapes_are_not_counted():
    before = _requests_count("GET", "/metrics", "200")

    await _get("/metrics")

    assert _requests_count("GET", "/metrics", "200") == before
