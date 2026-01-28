# API Reference

Complete API reference for the API Test Machine (ATM) REST API.

**Base URL:** `http://localhost:8000/api/v1`

---

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Health](#health)
  - [Runs](#runs)
  - [Tests](#tests)
  - [Schedules](#schedules)
  - [Storage](#storage)
- [Data Models](#data-models)
- [Error Handling](#error-handling)

---

## Quick Start

Get a load test running in 30 seconds:

```bash
# 1. Check the server is running
curl http://localhost:8000/api/v1/health

# 2. Start a simple load test
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {
      "name": "Quick Test",
      "url": "https://httpbin.org/get",
      "method": "GET",
      "total_requests": 10,
      "concurrency": 2
    }
  }'

# 3. Check the run status (replace {run_id} with the ID from step 2)
curl http://localhost:8000/api/v1/runs/{run_id}
```

---

## Authentication

The API supports two modes:

### Development Mode (Default)

No authentication required. All endpoints are accessible without an API key.

```bash
curl http://localhost:8000/api/v1/runs
```

### Production Mode

Enable by setting the `ATM_API_KEY` environment variable:

```bash
export ATM_API_KEY="your-secret-api-key"
```

Then include the key in requests:

```bash
curl http://localhost:8000/api/v1/runs \
  -H "X-API-Key: your-secret-api-key"
```

**Error Response (401 Unauthorized):**
```json
{
  "detail": "Invalid or missing API key"
}
```

---

## Endpoints

### Health

#### GET /health

Check if the server is running.

**Authentication:** Not required

```bash
curl http://localhost:8000/api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2024-01-28T12:00:00.000000"
}
```

---

### Runs

#### POST /runs

Start a new load test run.

**Authentication:** Required in production

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "spec": {
      "name": "Homepage Load Test",
      "url": "https://example.com",
      "method": "GET",
      "total_requests": 100,
      "concurrency": 10,
      "timeout_seconds": 30,
      "thresholds": {
        "max_latency_p95_ms": 500,
        "max_error_rate": 0.01
      }
    }
  }'
```

**Response (202 Accepted):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Run started"
}
```

**With POST body and headers:**

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {
      "name": "Create User Test",
      "url": "https://api.example.com/users",
      "method": "POST",
      "headers": {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      "body": {
        "name": "Test User",
        "email": "test@example.com"
      },
      "total_requests": 50,
      "concurrency": 5,
      "expected_status_codes": [201]
    }
  }'
```

**With authentication (Bearer token):**

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {
      "name": "Authenticated API Test",
      "url": "https://api.example.com/protected",
      "method": "GET",
      "auth": {
        "type": "bearer_token",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      },
      "total_requests": 100,
      "concurrency": 10
    }
  }'
```

**Multi-endpoint test:**

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {
      "name": "API Flow Test",
      "endpoints": [
        {
          "name": "list-users",
          "url": "https://api.example.com/users",
          "method": "GET",
          "weight": 3
        },
        {
          "name": "get-user",
          "url": "https://api.example.com/users/1",
          "method": "GET",
          "weight": 2
        },
        {
          "name": "create-user",
          "url": "https://api.example.com/users",
          "method": "POST",
          "body": {"name": "Test", "email": "test@example.com"},
          "weight": 1,
          "expected_status_codes": [201]
        }
      ],
      "distribution_strategy": "weighted",
      "total_requests": 100,
      "concurrency": 10
    }
  }'
```

---

#### GET /runs

List all test runs with optional filtering.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Results per page (1-200) |
| `offset` | int | 0 | Number of results to skip |
| `status` | string | - | Filter by status: `pending`, `running`, `completed`, `cancelled`, `failed` |

```bash
# List recent runs
curl "http://localhost:8000/api/v1/runs"

# List completed runs only
curl "http://localhost:8000/api/v1/runs?status=completed"

# Paginate results
curl "http://localhost:8000/api/v1/runs?limit=10&offset=20"
```

**Response (200 OK):**
```json
{
  "runs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Homepage Load Test",
      "status": "completed",
      "started_at": "2024-01-28T12:00:00.000000",
      "completed_at": "2024-01-28T12:01:30.000000",
      "total_requests": 100,
      "requests_completed": 100,
      "passed": true
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "API Stress Test",
      "status": "running",
      "started_at": "2024-01-28T12:05:00.000000",
      "completed_at": null,
      "total_requests": 1000,
      "requests_completed": 450,
      "passed": null
    }
  ],
  "total": 150
}
```

---

#### GET /runs/{run_id}

Get detailed information about a specific run.

```bash
curl "http://localhost:8000/api/v1/runs/550e8400-e29b-41d4-a716-446655440000"
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "spec": {
    "name": "Homepage Load Test",
    "url": "https://example.com",
    "method": "GET",
    "total_requests": 100,
    "concurrency": 10,
    "timeout_seconds": 30.0,
    "thresholds": {
      "max_latency_p95_ms": 500,
      "max_error_rate": 0.01
    }
  },
  "status": "completed",
  "started_at": "2024-01-28T12:00:00.000000",
  "completed_at": "2024-01-28T12:01:30.000000",
  "metrics": {
    "total_requests": 100,
    "successful_requests": 99,
    "failed_requests": 1,
    "latency_min_ms": 45.2,
    "latency_max_ms": 523.8,
    "latency_mean_ms": 120.5,
    "latency_p50_ms": 110.0,
    "latency_p90_ms": 280.0,
    "latency_p95_ms": 420.0,
    "latency_p99_ms": 510.0,
    "requests_per_second": 90.5,
    "duration_seconds": 1.1,
    "error_rate": 0.01,
    "errors_by_type": {
      "timeout": 1
    },
    "status_code_counts": {
      "200": 99,
      "408": 1
    },
    "total_bytes_received": 245000
  },
  "passed": true,
  "failure_reasons": [],
  "requests_completed": 100,
  "error_message": null,
  "sampled_requests": [
    {
      "request_number": 1,
      "status_code": 200,
      "latency_ms": 125.5,
      "error": null,
      "timestamp": "2024-01-28T12:00:00.500000",
      "response_size_bytes": 2048,
      "endpoint_name": null
    }
  ],
  "endpoint_metrics": []
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Run not found"
}
```

---

#### POST /runs/{run_id}/cancel

Cancel a running test.

```bash
curl -X POST "http://localhost:8000/api/v1/runs/550e8400-e29b-41d4-a716-446655440000/cancel"
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "message": "Cancellation requested"
}
```

**Response (409 Conflict):**
```json
{
  "detail": "Run is not in a cancellable state"
}
```

---

#### GET /runs/{run_id}/requests/{request_number}

Get detailed information about a specific request within a run.

```bash
curl "http://localhost:8000/api/v1/runs/550e8400-e29b-41d4-a716-446655440000/requests/1"
```

**Response (200 OK):**
```json
{
  "request_number": 1,
  "status_code": 200,
  "latency_ms": 125.5,
  "error": null,
  "timestamp": "2024-01-28T12:00:00.500000",
  "response_size_bytes": 2048,
  "endpoint_name": null,
  "request_url": "https://example.com",
  "request_method": "GET",
  "request_headers": {
    "User-Agent": "httpx/0.25.0",
    "Accept": "*/*"
  },
  "request_body": null,
  "response_headers": {
    "Content-Type": "text/html; charset=UTF-8",
    "Content-Length": "2048"
  },
  "response_body": "<!DOCTYPE html>..."
}
```

---

#### DELETE /runs/{run_id}

Delete a completed run and its data.

```bash
curl -X DELETE "http://localhost:8000/api/v1/runs/550e8400-e29b-41d4-a716-446655440000"
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Run deleted"
}
```

**Response (409 Conflict):**
```json
{
  "detail": "Run {id} is currently running. Cancel it first."
}
```

---

### Tests

#### GET /tests

List saved test configurations.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled_only` | bool | false | Only return enabled test configs |

```bash
# List all test configs
curl "http://localhost:8000/api/v1/tests"

# List only enabled configs
curl "http://localhost:8000/api/v1/tests?enabled_only=true"
```

**Response (200 OK):**
```json
{
  "configs": [
    {
      "name": "API Health Check",
      "enabled": true,
      "spec": {
        "name": "API Health Check",
        "url": "https://api.example.com/health",
        "method": "GET",
        "total_requests": 10,
        "concurrency": 2
      },
      "created_at": "2024-01-20T08:00:00.000000",
      "updated_at": "2024-01-28T10:00:00.000000",
      "run_count": 45
    }
  ],
  "total": 1
}
```

---

#### POST /tests/{name}/enabled

Enable or disable a test configuration.

```bash
# Enable a test
curl -X POST "http://localhost:8000/api/v1/tests/API%20Health%20Check/enabled" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Disable a test
curl -X POST "http://localhost:8000/api/v1/tests/API%20Health%20Check/enabled" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

**Response (200 OK):**
```json
{
  "name": "API Health Check",
  "enabled": true,
  "message": "Test 'API Health Check' enabled"
}
```

---

#### POST /tests/sync

Sync test configurations from existing runs. Creates a test config for each unique test name found in the run history.

```bash
curl -X POST "http://localhost:8000/api/v1/tests/sync"
```

**Response (200 OK):**
```json
{
  "message": "Synced 5 test configs",
  "synced": 5
}
```

---

#### POST /tests/run-all

Run all enabled test configurations.

**Request Body (optional):**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `repetitions` | int | 1 | Number of times to run each test |
| `max_concurrency` | int | 0 | Max concurrent tests (0 = unlimited) |

```bash
# Run all enabled tests once
curl -X POST "http://localhost:8000/api/v1/tests/run-all"

# Run all enabled tests 3 times each
curl -X POST "http://localhost:8000/api/v1/tests/run-all" \
  -H "Content-Type: application/json" \
  -d '{"repetitions": 3}'
```

**Response (202 Accepted):**
```json
{
  "batch_id": "770e8400-e29b-41d4-a716-446655440002",
  "total_tests": 5,
  "run_ids": [
    "880e8400-e29b-41d4-a716-446655440003",
    "880e8400-e29b-41d4-a716-446655440004",
    "880e8400-e29b-41d4-a716-446655440005",
    "880e8400-e29b-41d4-a716-446655440006",
    "880e8400-e29b-41d4-a716-446655440007"
  ],
  "message": "Started 5 test(s) in background"
}
```

---

#### GET /tests/report

Generate a PDF report of test configurations.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enabled_only` | bool | false | Only include enabled test configs |

```bash
# Download full report
curl "http://localhost:8000/api/v1/tests/report" -o test_report.pdf

# Download report of enabled tests only
curl "http://localhost:8000/api/v1/tests/report?enabled_only=true" -o enabled_tests.pdf
```

**Response:** PDF file (Content-Type: application/pdf)

---

### Schedules

#### POST /schedules

Create a new scheduled test.

**Cron Trigger:**

```bash
curl -X POST "http://localhost:8000/api/v1/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Health Check",
    "description": "Run health check every day at 8 AM UTC",
    "test_name": "API Health Check",
    "trigger": {
      "type": "cron",
      "hour": "8",
      "minute": "0",
      "day": "*",
      "month": "*",
      "day_of_week": "*",
      "timezone": "UTC"
    },
    "enabled": true,
    "tags": ["production", "daily"]
  }'
```

**Interval Trigger:**

```bash
curl -X POST "http://localhost:8000/api/v1/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hourly API Test",
    "description": "Run API test every hour",
    "test_name": "API Load Test",
    "trigger": {
      "type": "interval",
      "hours": 1
    },
    "enabled": true
  }'
```

**One-time (Date) Trigger:**

```bash
curl -X POST "http://localhost:8000/api/v1/schedules" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Release Day Test",
    "description": "Run stress test on release day",
    "test_name": "Stress Test",
    "trigger": {
      "type": "date",
      "run_date": "2024-02-01T14:30:00"
    },
    "max_runs": 1,
    "enabled": true
  }'
```

**Response (201 Created):**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440008",
  "name": "Daily Health Check",
  "description": "Run health check every day at 8 AM UTC",
  "test_name": "API Health Check",
  "trigger_type": "cron",
  "trigger": {
    "minute": "0",
    "hour": "8",
    "day": "*",
    "month": "*",
    "day_of_week": "*",
    "timezone": "UTC"
  },
  "max_runs": null,
  "run_count": 0,
  "enabled": true,
  "paused": false,
  "next_run_time": "2024-01-29T08:00:00.000000",
  "created_at": "2024-01-28T10:00:00.000000",
  "updated_at": "2024-01-28T10:00:00.000000",
  "tags": ["production", "daily"]
}
```

---

#### GET /schedules

List all schedules.

```bash
curl "http://localhost:8000/api/v1/schedules"
```

**Response (200 OK):**
```json
{
  "schedules": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440008",
      "name": "Daily Health Check",
      "description": "Run health check every day at 8 AM UTC",
      "test_name": "API Health Check",
      "trigger_type": "cron",
      "trigger": {
        "minute": "0",
        "hour": "8",
        "day": "*",
        "month": "*",
        "day_of_week": "*",
        "timezone": "UTC"
      },
      "max_runs": null,
      "run_count": 5,
      "enabled": true,
      "paused": false,
      "next_run_time": "2024-01-29T08:00:00.000000",
      "created_at": "2024-01-28T10:00:00.000000",
      "updated_at": "2024-01-28T10:00:00.000000",
      "tags": ["production", "daily"]
    }
  ],
  "total": 1
}
```

---

#### GET /schedules/{schedule_id}

Get details of a specific schedule.

```bash
curl "http://localhost:8000/api/v1/schedules/990e8400-e29b-41d4-a716-446655440008"
```

**Response (200 OK):**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440008",
  "name": "Daily Health Check",
  "description": "Run health check every day at 8 AM UTC",
  "test_name": "API Health Check",
  "trigger_type": "cron",
  "trigger": {
    "minute": "0",
    "hour": "8",
    "day": "*",
    "month": "*",
    "day_of_week": "*",
    "timezone": "UTC"
  },
  "max_runs": null,
  "run_count": 5,
  "enabled": true,
  "paused": false,
  "next_run_time": "2024-01-29T08:00:00.000000",
  "created_at": "2024-01-28T10:00:00.000000",
  "updated_at": "2024-01-28T10:00:00.000000",
  "tags": ["production", "daily"]
}
```

---

#### DELETE /schedules/{schedule_id}

Delete a schedule.

```bash
curl -X DELETE "http://localhost:8000/api/v1/schedules/990e8400-e29b-41d4-a716-446655440008"
```

**Response (200 OK):**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440008",
  "action": "delete",
  "success": true,
  "message": "Schedule deleted"
}
```

---

#### POST /schedules/{schedule_id}/pause

Pause a schedule (keeps it but stops execution).

```bash
curl -X POST "http://localhost:8000/api/v1/schedules/990e8400-e29b-41d4-a716-446655440008/pause"
```

**Response (200 OK):**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440008",
  "action": "pause",
  "success": true,
  "message": "Schedule paused"
}
```

---

#### POST /schedules/{schedule_id}/resume

Resume a paused schedule.

```bash
curl -X POST "http://localhost:8000/api/v1/schedules/990e8400-e29b-41d4-a716-446655440008/resume"
```

**Response (200 OK):**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440008",
  "action": "resume",
  "success": true,
  "message": "Schedule resumed"
}
```

---

### Storage

#### GET /storage/status

Get storage statistics and database information.

```bash
curl "http://localhost:8000/api/v1/storage/status"
```

**Response (200 OK):**
```json
{
  "storage_type": "sqlite",
  "database_path": "/path/to/data/atm.db",
  "database_size_bytes": 1024000,
  "database_size_human": "1.0 MB",
  "sqlite_version": "3.46.0",
  "total_runs": 150,
  "runs_by_status": [
    {"status": "completed", "count": 145},
    {"status": "failed", "count": 3},
    {"status": "cancelled", "count": 2}
  ],
  "runs_by_day": [
    {"date": "2024-01-28", "count": 50, "passed": 48, "failed": 2},
    {"date": "2024-01-27", "count": 45, "passed": 44, "failed": 1}
  ],
  "total_requests_stored": 15000,
  "avg_requests_per_run": 100,
  "oldest_run_date": "2024-01-20T08:00:00.000000",
  "newest_run_date": "2024-01-28T14:00:00.000000",
  "top_tests": [
    {"name": "API Health Check", "run_count": 45},
    {"name": "Homepage Load Test", "run_count": 30}
  ],
  "avg_run_duration_seconds": 1.2,
  "total_data_transferred_bytes": 3686400
}
```

---

## Data Models

### TestSpec

The core test specification defining what to test and how.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Test name (1-256 chars) |
| `description` | string | No | null | Optional description |
| `url` | string | No* | "" | Target URL (required for single-endpoint tests) |
| `method` | string | No | "GET" | HTTP method |
| `headers` | object | No | {} | Request headers |
| `body` | string/object | No | null | Request body (string or JSON object) |
| `endpoints` | array | No* | null | Multi-endpoint configuration |
| `distribution_strategy` | string | No | "round_robin" | How to distribute requests across endpoints |
| `total_requests` | int | No | 100 | Total requests to make (1-1,000,000) |
| `concurrency` | int | No | 10 | Concurrent connections (1-1000) |
| `requests_per_second` | float | No | null | Rate limit (null = unlimited) |
| `timeout_seconds` | float | No | 30.0 | Request timeout (1.0-300.0) |
| `thresholds` | object | No | {} | Pass/fail criteria |
| `expected_status_codes` | array | No | [200, 201, 204] | Status codes considered successful |
| `variables` | object | No | {} | Template variables |
| `auth` | object | No | null | Authentication configuration |

*Either `url` or `endpoints` must be provided.

**Example:**
```json
{
  "name": "User API Test",
  "url": "https://api.example.com/users",
  "method": "GET",
  "headers": {
    "Accept": "application/json"
  },
  "total_requests": 100,
  "concurrency": 10,
  "timeout_seconds": 30,
  "thresholds": {
    "max_latency_p95_ms": 500,
    "max_error_rate": 0.01
  },
  "expected_status_codes": [200]
}
```

---

### EndpointSpec

Configuration for a single endpoint in multi-endpoint tests.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Endpoint name (1-128 chars) |
| `url` | string | Yes | - | Target URL |
| `method` | string | No | "GET" | HTTP method |
| `headers` | object | No | {} | Request headers |
| `body` | string/object | No | null | Request body |
| `weight` | int | No | 1 | Weight for weighted distribution (1-100) |
| `expected_status_codes` | array | No | [200, 201, 204] | Success status codes |

**Example:**
```json
{
  "name": "get-users",
  "url": "https://api.example.com/users",
  "method": "GET",
  "weight": 3,
  "expected_status_codes": [200]
}
```

---

### Thresholds

Pass/fail criteria for a test run.

| Field | Type | Description |
|-------|------|-------------|
| `max_latency_p50_ms` | float | Maximum median latency in milliseconds |
| `max_latency_p95_ms` | float | Maximum 95th percentile latency |
| `max_latency_p99_ms` | float | Maximum 99th percentile latency |
| `max_error_rate` | float | Maximum error rate (0.0-1.0, e.g., 0.01 = 1%) |
| `min_throughput_rps` | float | Minimum requests per second |

**Example:**
```json
{
  "max_latency_p95_ms": 500,
  "max_error_rate": 0.01,
  "min_throughput_rps": 100
}
```

---

### Metrics

Collected metrics from a test run.

| Field | Type | Description |
|-------|------|-------------|
| `total_requests` | int | Total requests made |
| `successful_requests` | int | Requests that succeeded |
| `failed_requests` | int | Requests that failed |
| `latency_min_ms` | float | Minimum latency |
| `latency_max_ms` | float | Maximum latency |
| `latency_mean_ms` | float | Mean latency |
| `latency_p50_ms` | float | Median (50th percentile) latency |
| `latency_p90_ms` | float | 90th percentile latency |
| `latency_p95_ms` | float | 95th percentile latency |
| `latency_p99_ms` | float | 99th percentile latency |
| `requests_per_second` | float | Throughput |
| `duration_seconds` | float | Total test duration |
| `error_rate` | float | Error rate (0.0-1.0) |
| `errors_by_type` | object | Breakdown of errors by type |
| `status_code_counts` | object | Count of each status code |
| `total_bytes_received` | int | Total response data received |

---

### Authentication Types

#### API Key

```json
{
  "type": "api_key",
  "key": "your-api-key-value",
  "header_name": "X-API-Key"
}
```

#### Bearer Token

```json
{
  "type": "bearer_token",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### OAuth2 Client Credentials

```json
{
  "type": "oauth2_client_credentials",
  "token_url": "https://auth.example.com/oauth/token",
  "client_id": "your-client-id",
  "client_secret": "{{env:CLIENT_SECRET}}",
  "scope": "read write"
}
```

#### OAuth2 Password Grant

```json
{
  "type": "oauth2_password_grant",
  "token_url": "https://auth.example.com/oauth/token",
  "client_id": "your-client-id",
  "username": "user@example.com",
  "password": "{{env:USER_PASSWORD}}",
  "scope": "read write"
}
```

#### JWT

```json
{
  "type": "jwt",
  "secret": "{{env:JWT_SECRET}}",
  "algorithm": "HS256",
  "issuer": "my-app",
  "subject": "test-user",
  "audience": "api-server",
  "claims": {
    "role": "admin"
  },
  "expires_in_seconds": 3600
}
```

---

### Distribution Strategies

For multi-endpoint tests, control how requests are distributed:

| Strategy | Description |
|----------|-------------|
| `round_robin` | Cycles through endpoints: A → B → C → A → B → C... |
| `weighted` | Probability-based using endpoint weights |
| `sequential` | All requests to A, then all to B, then all to C |

---

### Template Variables

Dynamic values can be inserted into URLs, headers, and bodies:

| Variable | Example Output | Description |
|----------|---------------|-------------|
| `{{uuid}}` | `550e8400-e29b-41d4-a716-446655440000` | Random UUID4 |
| `{{timestamp}}` | `2024-01-28T14:30:45.123456` | ISO 8601 timestamp |
| `{{timestamp_unix}}` | `1706450445` | Unix timestamp (seconds) |
| `{{request_number}}` | `42` | Current request number (1-indexed) |
| `{{random_int}}` | `574829` | Random integer 0-999999 |
| `{{env:VAR_NAME}}` | (env value) | Environment variable |
| `{{target:NAME}}` | (env value) | TARGET_NAME environment variable |
| `{{custom_var}}` | (from spec) | Custom variable from spec.variables |

**Example with variables:**
```json
{
  "name": "Dynamic Test",
  "url": "https://api.example.com/users/{{uuid}}",
  "method": "POST",
  "headers": {
    "X-Request-ID": "{{uuid}}",
    "X-Timestamp": "{{timestamp}}"
  },
  "body": {
    "id": "{{request_number}}",
    "created_at": "{{timestamp}}"
  },
  "variables": {
    "custom_var": "my-value"
  },
  "total_requests": 100,
  "concurrency": 10
}
```

---

## Error Handling

### Error Response Format

All errors return a JSON object with a `detail` field:

```json
{
  "detail": "Human-readable error message"
}
```

### Common Error Codes

| Status | Description |
|--------|-------------|
| 400 | Invalid request body or parameters |
| 401 | Missing or invalid API key |
| 404 | Resource (run, schedule, etc.) not found |
| 409 | Action conflicts with current state |
| 422 | Request validation failed |
| 500 | Server error |

### Error Examples

**400 Bad Request:**
```json
{
  "detail": "total_requests must be between 1 and 1000000"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid or missing API key"
}
```

**404 Not Found:**
```json
{
  "detail": "Run not found"
}
```

**409 Conflict:**
```json
{
  "detail": "Run {id} is currently running. Cancel it first."
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "spec", "name"],
      "msg": "Field required"
    }
  ]
}
```

---

## HTTP Methods Reference

| Method | Endpoints |
|--------|-----------|
| GET | `/health`, `/runs`, `/runs/{id}`, `/runs/{id}/requests/{n}`, `/tests`, `/tests/report`, `/schedules`, `/schedules/{id}`, `/storage/status` |
| POST | `/runs`, `/runs/{id}/cancel`, `/tests/{name}/enabled`, `/tests/sync`, `/tests/run-all`, `/schedules`, `/schedules/{id}/pause`, `/schedules/{id}/resume` |
| DELETE | `/runs/{id}`, `/schedules/{id}` |

---

## Rate Limiting

The server does not impose rate limits on API requests. However, you can control the rate of load test requests using the `requests_per_second` field in TestSpec.

```json
{
  "spec": {
    "name": "Rate Limited Test",
    "url": "https://api.example.com/endpoint",
    "total_requests": 1000,
    "concurrency": 10,
    "requests_per_second": 50
  }
}
```

This limits the test to 50 requests per second regardless of concurrency level.
