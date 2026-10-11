import httpx
from typing import AsyncGenerator

from app.core.config import settings


class InferenceClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.inference_base_url).rstrip("/")

    async def chat_completion(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def chat_completion_stream(self, payload: dict) -> AsyncGenerator[str, None]:
        # ollama talks SSE here, so we hand back whole lines instead of byte soup.
        # aiter_bytes happily slices a "data: {...}" line in half, json.loads wasnt nice
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            ) as response:
                if response.is_error:
                    await response.aread() 
                    response.raise_for_status()
                async for line in response.aiter_lines():
                    if line: 
                        yield line

inference_client = InferenceClient()