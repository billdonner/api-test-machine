# API Test Machine

A REST API load testing system with multiple interfaces (CLI, MCP, WebApp) built on a Python async engine, with a rule-based agent layer for automation.

## Features

- **Async Test Engine**: High-performance HTTP load testing with httpx
- **Multi-Endpoint Testing**: Test multiple URLs in a single run with distribution strategies
- **Rate Limiting**: Token bucket algorithm for controlled request rates
- **Template Variables**: Dynamic URL and body substitution (`{{uuid}}`, `{{timestamp}}`, etc.)
- **Authentication**: Bearer tokens, API keys, and Basic auth support
- **Metrics**: Latency percentiles (P50/P90/P95/P99), throughput, error rates
- **Per-Endpoint Metrics**: Individual metrics for each endpoint in multi-endpoint tests
- **Thresholds**: Pass/fail criteria based on latency and error rates
- **Multiple Interfaces**:
  - REST API for programmatic access
  - CLI for command-line usage
  - MCP server for LLM agent integration
  - Web dashboard for visual monitoring
- **Scheduling**: Cron and interval-based test automation

## Quick Start

### Installation

```bash
# Clone and install
cd api-test-machine
pip install -e ".[dev]"
```

### Start the API Server

```bash
uvicorn api.main:app --reload
```

### Run a Test via CLI

Create a test spec file (`test-spec.json`):

```json
{
  "name": "API Health Check",
  "url": "https://httpbin.org/get",
  "method": "GET",
  "total_requests": 100,
  "concurrency": 10,
  "thresholds": {
    "max_latency_p95_ms": 500,
    "max_error_rate": 0.01
  }
}
```

Run the test:

```bash
atm run test-spec.json --wait
```

### Use the Web Dashboard

```bash
cd webapp
npm install
npm run dev
```

Open http://localhost:5173

## Multi-Endpoint Testing

Test multiple endpoints in a single run with different distribution strategies:

```json
{
  "name": "Stock API Test",
  "endpoints": [
    {"name": "AAPL", "url": "https://api.example.com/stock/AAPL", "weight": 1},
    {"name": "GOOGL", "url": "https://api.example.com/stock/GOOGL", "weight": 1},
    {"name": "MSFT", "url": "https://api.example.com/stock/MSFT", "weight": 1}
  ],
  "distribution_strategy": "round_robin",
  "total_requests": 300,
  "concurrency": 10
}
```

### Distribution Strategies

| Strategy | Behavior |
|----------|----------|
| `round_robin` | Requests cycle through endpoints: A, B, C, A, B, C... |
| `weighted` | Distribute based on weights (e.g., 3:1 = ~75%:25%) |
| `sequential` | All requests to A, then all to B, then C |

### Endpoint Configuration

Each endpoint supports:

```json
{
  "name": "Create User",
  "url": "https://api.example.com/users",
  "method": "POST",
  "headers": {"Content-Type": "application/json"},
  "body": {"name": "test"},
  "weight": 2,
  "expected_status_codes": [201]
}
```

## CLI Commands

```bash
# Run a test and wait for completion
atm run spec.json --wait --output results.json

# Check status of a run
atm status <run-id>

# Cancel a running test
atm cancel <run-id>

# List recent runs
atm list --limit 10 --status completed
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health` | No | Health check |
| POST | `/api/v1/runs` | Yes | Start test run |
| GET | `/api/v1/runs` | Yes | List recent runs |
| GET | `/api/v1/runs/{id}` | Yes | Get run status/metrics |
| POST | `/api/v1/runs/{id}/cancel` | Yes | Cancel running test |
| DELETE | `/api/v1/runs/{id}` | Yes | Delete a run |

## Test Specification

### Single Endpoint (Legacy)

```json
{
  "name": "Test Name",
  "description": "Optional description",
  "url": "https://api.example.com/endpoint/{{uuid}}",
  "method": "POST",
  "headers": {
    "Authorization": "Bearer {{env:API_TOKEN}}",
    "Content-Type": "application/json"
  },
  "body": {
    "timestamp": "{{timestamp}}",
    "request_id": "{{request_number}}"
  },
  "total_requests": 1000,
  "concurrency": 50,
  "requests_per_second": 100,
  "timeout_seconds": 30,
  "thresholds": {
    "max_latency_p50_ms": 100,
    "max_latency_p95_ms": 500,
    "max_latency_p99_ms": 1000,
    "max_error_rate": 0.01,
    "min_throughput_rps": 50
  },
  "expected_status_codes": [200, 201],
  "variables": {
    "custom_var": "value"
  }
}
```

### Multi-Endpoint

```json
{
  "name": "API Suite Test",
  "endpoints": [
    {
      "name": "Get Users",
      "url": "https://api.example.com/users",
      "method": "GET"
    },
    {
      "name": "Create User",
      "url": "https://api.example.com/users",
      "method": "POST",
      "body": {"name": "test"},
      "weight": 2
    }
  ],
  "distribution_strategy": "weighted",
  "total_requests": 1000,
  "concurrency": 50
}
```

## Template Variables

| Variable | Description |
|----------|-------------|
| `{{uuid}}` | Random UUID |
| `{{timestamp}}` | ISO timestamp |
| `{{timestamp_unix}}` | Unix timestamp |
| `{{request_number}}` | Request number (1-indexed) |
| `{{random_int}}` | Random integer 0-999999 |
| `{{env:VAR_NAME}}` | Environment variable |
| `{{target:NAME}}` | TARGET_NAME environment variable |
| `{{custom}}` | Custom variable from spec.variables |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_TEST_MACHINE_API_KEY` | API key for authentication (optional in dev) |
| `ATM_API_URL` | API server URL for CLI/MCP (default: http://localhost:8000) |
| `ATM_API_KEY` | API key for CLI/MCP clients |
| `ATM_DATA_DIR` | Data directory (default: ./data) |

## MCP Server

The MCP server provides tools for LLM agents. See [docs/MCP_GUIDE.md](docs/MCP_GUIDE.md) for details.

```bash
python -m mcp_server.server
```

Available tools:
- `run_api_test` - Execute a load test
- `get_test_status` - Get run status by ID
- `get_test_results` - Get detailed results
- `cancel_test` - Cancel a running test
- `list_recent_tests` - List recent runs
- `create_test_spec` - Generate test spec JSON
- `rerun_test` - Re-run a test by name

## Agent Scheduler

Run scheduled tests automatically:

```bash
python -m agent.main
```

## Development

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific module
pytest tests/engine/

# Multi-endpoint tests
pytest tests/engine/test_multi_endpoint.py -v
```

### Project Structure

```
api-test-machine/
├── engine/          # Core async test engine
│   ├── models.py    # Pydantic models (TestSpec, EndpointSpec, etc.)
│   ├── executor.py  # Request execution and distribution
│   ├── metrics.py   # Metrics collection and aggregation
│   ├── auth.py      # Authentication providers
│   └── templating.py # Variable substitution
├── api/             # FastAPI Control API
├── cli/             # Typer CLI
├── agent/           # Scheduler and orchestration
├── mcp_server/      # MCP server for LLM agents
├── webapp/          # SvelteKit dashboard
├── tests/           # Test suite
├── docs/            # Documentation
└── data/            # Runtime data (gitignored)
```

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [MCP User Guide](docs/MCP_GUIDE.md)

## License

MIT
