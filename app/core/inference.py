import httpx

from app.core.config import settings


class InferenceClient:
    """
    Wraps whatever's running at INFERENCE_BASE_URL.
    Ollama and vLLM both expose an OpenAI-compatible /v1/chat/completions
    endpoint, so this class never needs to know which one it's calling.
    """

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


inference_client = InferenceClient()