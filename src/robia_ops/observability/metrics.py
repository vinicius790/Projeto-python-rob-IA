from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "robia_http_requests_total",
    "HTTP requests handled by RobIA Ops",
    labelnames=("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "robia_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
PAYMENT_PROCESSING = Counter(
    "robia_payment_processing_total",
    "Payment provider processing outcomes",
    labelnames=("provider", "outcome", "dry_run"),
)
