---
name: observability-patterns
description: "Observability: structured logging, metrics (RED/USE/four golden signals), distributed tracing (OpenTelemetry), correlation IDs, log aggregation, SLO/SLI. Triggers: logging, log level, metrics, Prometheus, Grafana, OpenTelemetry, trace, span, structured log, observability, monitoring, SLO, SLI, alerting. Load when adding or reviewing logs, metrics, or traces."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Observability Patterns

## Structured Logging

### Python (structlog)
```python
import structlog

logger = structlog.get_logger()

logger.info("user_created", user_id=user.id, email=user.email, source="api")
logger.error("payment_failed", order_id=order.id, error=str(e), amount=amount)
```

### Node.js (Pino)
```typescript
import pino from "pino";

const logger = pino({ level: "info", transport: { target: "pino-pretty" } });

logger.info({ userId: user.id, action: "login" }, "User logged in");
logger.error({ err, orderId: order.id }, "Payment processing failed");
```

### Log Levels
| Level | Use For |
|-------|---------|
| `error` | Failures requiring attention |
| `warn` | Unexpected but handled situations |
| `info` | Business events, state transitions |
| `debug` | Development diagnostics |

### Rules
- Always use structured key-value pairs, not string interpolation
- Include correlation IDs for request tracing
- Never log sensitive data (passwords, tokens, PII)
- Log at boundaries: API entry/exit, external calls, state changes

## OpenTelemetry

### Python Setup
```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
)

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

request_counter = meter.create_counter("http_requests_total", description="Total HTTP requests")
request_duration = meter.create_histogram("http_request_duration_seconds")

@tracer.start_as_current_span("process_order")
def process_order(order_id: str):
    request_counter.add(1, {"method": "POST", "endpoint": "/orders"})
    with tracer.start_as_current_span("validate_order"):
        validate(order_id)
    with tracer.start_as_current_span("charge_payment"):
        charge(order_id)
```

### Node.js Setup
```typescript
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-grpc";

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({ url: "http://otel-collector:4317" }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
```

## Prometheus Metrics

### Metric Types
```python
# Counter - monotonically increasing (requests, errors)
http_requests_total = Counter("http_requests_total", "Total requests", ["method", "status", "path"])

# Histogram - distribution (latency, sizes)
request_duration = Histogram("request_duration_seconds", "Request latency",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0])

# Gauge - current value (connections, queue size)
active_connections = Gauge("active_connections", "Current active connections")
```

### Key Metrics (RED Method)
| Metric | Type | Purpose |
|--------|------|---------|
| Request **R**ate | Counter | Traffic volume |
| Request **E**rrors | Counter | Error rate |
| Request **D**uration | Histogram | Latency distribution |

### Key Metrics (USE Method - Infrastructure)
| Metric | Type | Purpose |
|--------|------|---------|
| **U**tilization | Gauge | % resource used |
| **S**aturation | Gauge | Queue depth |
| **E**rrors | Counter | Error count |

## Health Check Endpoints

```python
# FastAPI example
@app.get("/health")
async def health():
    checks = {
        "database": await check_db(),
        "redis": await check_redis(),
        "disk": check_disk_space(),
    }
    status = "healthy" if all(checks.values()) else "degraded"
    code = 200 if status == "healthy" else 503
    return JSONResponse({"status": status, "checks": checks}, status_code=code)

@app.get("/ready")
async def readiness():
    """Kubernetes readiness probe - can this instance serve traffic?"""
    return {"ready": True}

@app.get("/live")
async def liveness():
    """Kubernetes liveness probe - is the process alive?"""
    return {"alive": True}
```

## Error Tracking (Sentry)

```python
import sentry_sdk

sentry_sdk.init(
    dsn="https://key@sentry.io/project",
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    environment="production",
)

# Automatic exception capture + manual context
with sentry_sdk.push_scope() as scope:
    scope.set_tag("order_id", order.id)
    scope.set_context("payment", {"amount": amount, "currency": "USD"})
    sentry_sdk.capture_exception(e)
```

## SLI/SLO Definition

### Example SLOs
| Service | SLI | SLO | Window |
|---------|-----|-----|--------|
| API | Availability (2xx / total) | 99.9% | 30 days |
| API | Latency p99 | < 500ms | 30 days |
| Search | Result relevance | > 80% | 7 days |
| Ingest | Processing success rate | 99.5% | 30 days |

### Error Budget
```
Error Budget = 1 - SLO = 1 - 0.999 = 0.1%
Monthly budget = 30 days * 24h * 60min * 0.001 = 43.2 minutes
```

## Alerting Rules

### Prometheus Alert Examples
```yaml
groups:
  - name: api-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 5% for 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(request_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
```

### Alert Best Practices
- Alert on symptoms (high latency), not causes (high CPU)
- Include runbook links in annotations
- Set appropriate severity: page only for user-impacting issues
- Use `for` duration to avoid flapping
