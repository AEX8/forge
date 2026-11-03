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
        # force streaming on and ask for token counts in the last chunk,
        # otherwise we stream a whole essay and have no idea what it cost
        stream_payload = {
            **payload,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                json=stream_payload,
            ) as response:
                response.raise_for_status()
                # aiter_lines stitches split chunks back into whole lines for us
                async for line in response.aiter_lines():
                    if line:
                        yield line

inference_client = InferenceClient()