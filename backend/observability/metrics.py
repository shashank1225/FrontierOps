from prometheus_client import Counter, Histogram

API_REQUESTS = Counter(
    "frontierops_api_requests_total",
    "HTTP requests handled by FrontierOps.",
    ("method", "route", "status_code"),
)
API_DURATION = Histogram(
    "frontierops_api_request_duration_seconds",
    "HTTP request duration.",
    ("method", "route"),
)
MODEL_CALLS = Counter(
    "frontierops_model_calls_total",
    "LLM provider calls.",
    ("provider", "model", "status"),
)
MODEL_LATENCY = Histogram(
    "frontierops_model_call_duration_seconds",
    "End-to-end LLM call duration.",
    ("provider", "model"),
)
MODEL_TOKENS = Counter(
    "frontierops_model_tokens_total",
    "Tokens processed by LLM calls.",
    ("provider", "model", "direction"),
)
EVALUATION_RUNS = Counter(
    "frontierops_evaluation_runs_total",
    "Evaluation runs by terminal state and release decision.",
    ("status", "release_decision"),
)
EVALUATION_DURATION = Histogram(
    "frontierops_evaluation_duration_seconds",
    "Evaluation run duration.",
    ("provider", "model"),
)
WORKER_JOBS = Counter(
    "frontierops_worker_jobs_total",
    "Evaluation jobs handled by workers.",
    ("status",),
)
