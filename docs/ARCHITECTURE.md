# API Test Machine - Architecture Overview

## System Overview

API Test Machine is a load testing platform designed for REST API testing with multiple access interfaces. The system follows a layered architecture with clear separation between the core engine, storage layer, API layer, and client interfaces.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Interfaces                         │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│   Web App   │    CLI      │ MCP Server  │   Agent     │   API   │
│  (SvelteKit)│   (Typer)   │  (stdio)    │ (Scheduler) │ Clients │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴────┬────┘
       │             │             │             │           │
       └─────────────┴─────────────┴─────────────┴───────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     FastAPI Control API      │
                    │   (REST + WebSocket/SSE)     │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
   ┌──────────▼──────────┐  ┌──────▼──────┐  ┌─────────▼─────────┐
   │   Storage Layer      │  │ Test Engine │  │  Metrics System   │
   │  (SQLite/JSON)       │  │  (httpx)    │  │  (Per-endpoint)   │
   └──────────────────────┘  └─────────────┘  └───────────────────┘
```

## Core Components

### 1. Test Engine (`engine/`)

The heart of the system - an async Python engine for executing HTTP load tests.

**Key Modules:**

| Module | Purpose |
|--------|---------|
| `models.py` | Pydantic models for test specs, results, and metrics |
| `executor.py` | Async request execution with concurrency control |
| `metrics.py` | Real-time metrics collection and aggregation |
| `auth.py` | Authentication providers (Bearer, API Key, Basic) |
| `templating.py` | Variable substitution engine |
| `rate_limiter.py` | Token bucket rate limiting |

**Data Flow:**

```
TestSpec → Executor → [RequestResult...] → MetricsCollector → RunResult
              │
              ├── EndpointSelector (multi-endpoint)
              ├── RateLimiter
              ├── TemplateEngine
              └── AuthProvider
```

### 2. Storage Layer (`api/`)

Persistent storage with pluggable backends and unified interface.

**Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│                  StorageInterface                        │
│     (Protocol: init, save, load, delete, list_runs)     │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│  SQLiteStorage  │      │ AsyncJSONStorage │
│   (default)     │      │   (fallback)    │
├─────────────────┤      ├─────────────────┤
│ SQLAlchemy 2.0  │      │ JSON files in   │
│ + aiosqlite     │      │ data/runs/      │
│ data/atm.db     │      │                 │
└─────────────────┘      └─────────────────┘
```

**Key Components:**

| File | Purpose |
|------|---------|
| `storage_base.py` | StorageInterface protocol and factory |
| `sqlite_storage.py` | SQLite implementation with async queries |
| `database.py` | SQLAlchemy models and connection management |
| `storage.py` | Legacy JSON file storage |

**Database Schema:**

```sql
CREATE TABLE runs (
    id              VARCHAR(36) PRIMARY KEY,
    name            VARCHAR(256) NOT NULL,
    url             TEXT,
    method          VARCHAR(10),
    total_requests  INTEGER,
    concurrency     INTEGER,
    status          VARCHAR(20) NOT NULL,
    started_at      DATETIME,
    completed_at    DATETIME,
    created_at      DATETIME,
    passed          BOOLEAN,
    requests_completed INTEGER,
    error_message   TEXT,
    spec_json       JSON NOT NULL,
    metrics_json    JSON,
    failure_reasons_json JSON,
    endpoint_metrics_json JSON,
    sampled_requests_json JSON
);
```

**Migrations:**

Alembic manages schema migrations:

```bash
alembic upgrade head      # Apply migrations
alembic revision -m "..."  # Create new migration
alembic current           # Check version
```

### 3. Multi-Endpoint System

The multi-endpoint feature allows testing multiple URLs in a single run.

**Components:**

```
┌─────────────────────────────────────────────────────────┐
│                     TestSpec                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │  endpoints: [EndpointSpec, EndpointSpec, ...]   │    │
│  │  distribution_strategy: round_robin|weighted|seq │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │     EndpointSelector       │
         │  Selects endpoint per req  │
         └─────────────┬─────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    ▼                  ▼                  ▼
 Endpoint A        Endpoint B        Endpoint C
    │                  │                  │
    └──────────────────┼──────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │ EndpointMetricsCollector   │
         │  Per-endpoint + aggregate  │
         └───────────────────────────┘
```

**Distribution Strategies:**

- **Round Robin**: Cycles through endpoints sequentially (A→B→C→A→B→C...)
- **Weighted**: Probability-based selection using weights
- **Sequential**: Completes all requests to each endpoint before moving to next

### 4. Control API (`api/`)

FastAPI-based REST API for test management.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/runs` | Start new test run |
| GET | `/api/v1/runs` | List runs with filters |
| GET | `/api/v1/runs/{id}` | Get run details + metrics |
| POST | `/api/v1/runs/{id}/cancel` | Cancel running test |
| DELETE | `/api/v1/runs/{id}` | Delete run |
| GET | `/api/v1/storage/status` | Storage statistics |

**Run Lifecycle:**

```
PENDING → RUNNING → COMPLETED
                 ↘ CANCELLED
                 ↘ FAILED
```

### 5. Web Dashboard (`webapp/`)

SvelteKit single-page application for visual test management.

**Pages:**

| Route | Purpose |
|-------|---------|
| `/` | Dashboard with grouped runs, stats, filters |
| `/new` | Create new test (single or multi-endpoint) |
| `/runs/[id]` | Run details, metrics, request viewer |
| `/edit/[id]` | Edit existing test configuration |
| `/storage` | Storage status and health monitoring |

**Features:**
- Real-time run progress with live metrics
- Results visualization (charts, per-endpoint breakdown)
- Request/response sampling viewer
- Storage health dashboard with charts

### 6. MCP Server (`mcp_server/`)

Model Context Protocol server for LLM agent integration.

**Tools:**
- `run_api_test` - Execute tests
- `get_test_status` - Check progress
- `get_test_results` - Retrieve results
- `list_recent_tests` - Browse history
- `rerun_test` - Re-run by name
- `cancel_test` - Stop running tests
- `create_test_spec` - Generate JSON specs

### 7. Agent Scheduler (`agent/`)

Automated test execution with scheduling support.

## Key Design Decisions

### 1. Backward Compatibility

The multi-endpoint feature maintains full backward compatibility:
- Single-URL specs work unchanged
- `get_endpoints()` helper provides unified handling
- API responses include both aggregate and per-endpoint metrics

### 2. Async-First Architecture

All I/O operations use Python's async/await:
- httpx AsyncClient for HTTP requests
- asyncio Semaphore for concurrency control
- aiosqlite for async database operations
- Non-blocking rate limiting

### 3. Pluggable Storage

Storage backends implement a common protocol:
- SQLite for production (default)
- JSON files for development/debugging
- Easy to add PostgreSQL or other backends

### 4. Real-Time Metrics

Metrics are computed incrementally during test execution:
- Live progress updates via polling
- Sampled request/response data for debugging
- Per-endpoint breakdown in multi-endpoint tests

### 5. Pluggable Authentication

Authentication is configured per-test via `AuthConfig`:
```python
auth = AuthConfig(
    type=AuthType.BEARER,
    token="{{env:API_TOKEN}}"  # Supports template variables
)
```

## Data Models

### Core Models Hierarchy

```
TestSpec
├── name, description
├── url, method, headers, body (single endpoint)
├── endpoints: [EndpointSpec] (multi-endpoint)
├── distribution_strategy
├── total_requests, concurrency, requests_per_second
├── timeout_seconds
├── thresholds: Thresholds
├── expected_status_codes
├── variables
└── auth: AuthConfig

EndpointSpec
├── name, url, method
├── headers, body
├── weight
└── expected_status_codes

RunResult
├── id, spec, status
├── started_at, completed_at
├── metrics: Metrics (aggregate)
├── endpoint_metrics: [EndpointMetrics] (per-endpoint)
├── passed, failure_reasons
├── requests_completed
└── sampled_requests

Metrics
├── total/successful/failed requests
├── latency percentiles (min/max/mean/p50/p90/p95/p99)
├── requests_per_second, duration_seconds
├── error_rate, errors_by_type
└── status_code_counts
```

## Deployment

### Development

```bash
# Backend
uvicorn api.app:app --reload

# Frontend
cd webapp && npm run dev
```

### Production

```bash
# Apply migrations
alembic upgrade head

# Backend with workers
uvicorn api.app:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend build
cd webapp && npm run build
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| HTTP Client | httpx (async) |
| API Framework | FastAPI |
| Data Validation | Pydantic v2 |
| Database | SQLAlchemy 2.0 + aiosqlite |
| Migrations | Alembic |
| CLI | Typer + Rich |
| Web Frontend | SvelteKit + Tailwind |
| Charts | Chart.js |
| LLM Integration | MCP SDK |

## Future Considerations

- Distributed execution across multiple workers
- PostgreSQL support for larger deployments
- GraphQL API alternative
- WebSocket for real-time updates
- Custom scripting/hooks support
- Prometheus metrics export
