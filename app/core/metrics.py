from prometheus_client import Counter, Histogram

# CPU inference takes 15 to 70 seconds, so the default buckets (max 10s)
# would put almost every request in +Inf. These go up to 2 minutes.
LATENCY_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30, 45, 60, 90, 120)
TTFT_BUCKETS = (0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60)

# Gateway level, recorded by the middleware for every request.
# route is the path template (e.g. /v1/chat/completions), never the raw URL,
# so the number of label values stays small.
HTTP_REQUESTS = Counter(
    "forge_http_requests_total",
    "HTTP requests handled by the gateway",
    ["method", "route", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "forge_http_request_duration_seconds",
    "Time from request received to response returned",
    ["method", "route"],
    buckets=LATENCY_BUCKETS,
)

# LLM level, recorded in the chat router.
TOKENS = Counter(
    "forge_tokens_total",
    "Tokens processed, split by direction",
    ["model", "direction"],  # direction is "in" (prompt) or "out" (completion)
)
INFERENCE_DURATION = Histogram(
    "forge_inference_duration_seconds",
    "Time spent waiting on the inference backend",
    ["model", "stream"],
    buckets=LATENCY_BUCKETS,
)
TIME_TO_FIRST_TOKEN = Histogram(
    "forge_time_to_first_token_seconds",
    "Time until the first streamed chunk arrives from the backend",
    ["model"],
    buckets=TTFT_BUCKETS,
)
RATE_LIMITED = Counter(
    "forge_rate_limited_total",
    "Requests rejected with 429 by the rate limiter",
)
PROMPT_RISK = Counter(
    "forge_prompt_risk_total",
    "Prompt risk assessments, by result level",
    ["level"],
)
