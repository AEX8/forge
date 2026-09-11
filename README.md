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

Create a test client and API key:

```bash
python -m scripts.create_client "Test Client"
```

Then:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:1b",
    "messages": [{"role": "user", "content": "Explain Kubernetes in one sentence"}]
  }'
```

## Running tests

```bash
docker compose up -d postgres redis
pytest -v
```

## Known limitations

- **Ollama runs CPU-only inside Docker on Apple Silicon.** Docker Desktop's Linux VM doesn't get Metal GPU passthrough, so containerized inference is noticeably slower than running Ollama natively. This is a known, accepted tradeoff for local development; production targets GPU-backed infrastructure.
- **Auth dependency holds a database connection for the full request lifetime**, including the slow inference call. Under high concurrency this can exhaust the connection pool; current mitigation is a larger pool size, a proper fix would release the session before the inference call.
- **Prompt-risk detection is heuristic**, not a trained classifier. It catches known patterns, not novel phrasing. Framed as "risk detection and policy enforcement," not a guarantee against injection.
- **One API key per client assumed** in the current auth flow. The schema supports multiple keys per client, but the code path doesn't yet.

## Tech stack

FastAPI · PostgreSQL · SQLAlchemy · Alembic · Redis · Ollama / vLLM · Docker · Kubernetes (planned) · Terraform (planned) · Prometheus/Grafana (planned) · React (planned)

## License

MIT




## Tech stack

FastAPI, PostgreSQL, Redis, Ollama / vLLM, Kubernetes, Terraform, Prometheus/Grafana, React

## License

MIT
