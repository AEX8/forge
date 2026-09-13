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

    async def chat_completion_stream(self, payload: dict) -> AsyncGenerator[bytes, None]:
        # different beast entirely, we're handing chunks back as they arrive
        # instead of waiting around for the whole response like a normal person
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk


inference_client = InferenceClient()