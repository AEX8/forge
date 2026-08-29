# Forge

A self-hosted, OpenAI-compatible LLM gateway. Run your own private Llama model with the same developer experience as a commercial LLM API, but with authentication, rate limiting, usage metering, prompt risk detection, and observability built in.

## Why

Companies using commercial LLM APIs give up three things: control over where their data goes, predictable costs at scale, and visibility into what's actually happening with every request. Forge puts a self-hosted model behind an API that looks and behaves like OpenAI's or Anthropic's, so you get the same integration experience without any of that trade-off.

## Architecture (short version)

```
Client -> Forge Gateway (FastAPI) -> Inference backend (Ollama / vLLM) -> Llama
              │
              ├── API key auth
              ├── Redis rate limiting
              ├── Prompt-risk detection
              ├── Usage metering + structured logs
              └── Prometheus metrics
```

## Local development

```bash
cp .env.example .env
docker compose up --build
```

Then:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer fk_live_dev" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:1b",
    "messages": [{"role": "user", "content": "Explain Kubernetes in one sentence"}]
  }'
```

## Tech stack

FastAPI, PostgreSQL, Redis, Ollama / vLLM, Kubernetes, Terraform, Prometheus/Grafana, React

## License

MIT
