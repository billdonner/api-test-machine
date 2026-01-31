# MCP User Guide

This guide explains how to use API Test Machine with LLM agents through the Model Context Protocol (MCP).

## What is MCP?

MCP (Model Context Protocol) allows LLM agents like Claude to interact with external tools. API Test Machine provides an MCP server that exposes **13 tools** for load testing and schedule management.

## Setup

### 1. Start the API Server

The MCP server communicates with the API server, so start it first:

```bash
cd api-test-machine
uvicorn api.main:app --reload
```

### 2. Configure MCP Server

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "api-test-machine": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/api-test-machine",
      "env": {
        "ATM_API_URL": "http://localhost:8000",
        "ATM_API_KEY": "your-api-key"
      }
    }
  }
}
```

### 3. Verify Connection

Ask Claude: "What API testing tools do you have available?"

Claude should list the available tools from API Test Machine.

## Available Tools

### run_api_test

Execute a load test against an API endpoint.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Name for the test run |
| `url` | string | Yes | Target URL to test |
| `method` | string | No | HTTP method (GET, POST, etc.) |
| `total_requests` | integer | No | Number of requests (default: 100) |
| `concurrency` | integer | No | Concurrent requests (default: 10) |
| `requests_per_second` | number | No | Rate limit |
| `headers` | object | No | HTTP headers |
| `body` | string | No | Request body (JSON string) |

**Example prompt:**
> "Run a load test against https://api.example.com/users with 200 requests and 20 concurrent connections"

### get_test_status

Check the status and results of a running or completed test.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `run_id` | string | Yes | ID of the test run |

**Example prompt:**
> "What's the status of test run abc123?"

### get_test_results

Get detailed results for a specific run or all runs matching a name.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `run_id` | string | No | Specific run ID |
| `test_name` | string | No | Name to search for |
| `limit` | integer | No | Max results (default: 10) |

**Example prompts:**
> "Show me the results for run abc123"
> "Get all results for the 'API Health Check' test"

### list_recent_tests

List recent test runs with optional filtering.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | integer | No | Number of runs (default: 10) |
| `status` | string | No | Filter by status |

**Example prompts:**
> "Show me the last 5 test runs"
> "List all failed tests"

### rerun_test

Re-run an existing test by name.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `test_name` | string | Yes | Name of the test to re-run |

**Example prompt:**
> "Rerun the 'Production API Check' test"

### cancel_test

Cancel a running test.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `run_id` | string | Yes | ID of the run to cancel |

**Example prompt:**
> "Cancel test run abc123"

### create_test_spec

Generate a reusable test specification JSON.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Test name |
| `url` | string | Yes | Target URL |
| `method` | string | No | HTTP method |
| `total_requests` | integer | No | Request count |
| `concurrency` | integer | No | Concurrency level |
| `max_latency_p95_ms` | number | No | P95 latency threshold |
| `max_error_rate` | number | No | Error rate threshold (0-1) |

**Example prompt:**
> "Create a test spec for testing our payments API with a 500ms latency threshold"

---

## Schedule Management Tools

### create_schedule

Create a new schedule to run tests automatically.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Schedule name |
| `test_name` | string | Yes | Test to run |
| `trigger_type` | string | Yes | `interval`, `cron`, or `date` |
| `interval_hours` | integer | No | Hours between runs |
| `interval_minutes` | integer | No | Minutes between runs |
| `cron_expression` | string | No | Cron: `minute hour day month day_of_week` |
| `run_date` | string | No | ISO 8601 date for one-time run |
| `max_runs` | integer | No | Limit total runs |
| `enabled` | boolean | No | Enable schedule (default: true) |
| `tags` | array | No | Tags for categorization |

**Example prompts:**
> "Create a schedule to run the 'API Health Check' test every hour"
> "Schedule the 'Load Test' to run daily at 8am UTC"
> "Create a one-time schedule to run 'Release Test' on Feb 1st at 10am"

### list_schedules

List all schedules with optional filtering.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `enabled` | boolean | No | Filter by enabled status |
| `tag` | string | No | Filter by tag |
| `limit` | integer | No | Max results (default: 50) |

**Example prompts:**
> "Show me all my schedules"
> "List enabled schedules"

### get_schedule

Get details of a specific schedule.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `schedule_id` | string | Yes | Schedule ID |

**Example prompt:**
> "Show me details for schedule abc123"

### pause_schedule

Temporarily pause a schedule.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `schedule_id` | string | Yes | Schedule ID |

**Example prompt:**
> "Pause the daily health check schedule"

### resume_schedule

Resume a paused schedule.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `schedule_id` | string | Yes | Schedule ID |

**Example prompt:**
> "Resume the paused schedule"

### delete_schedule

Permanently delete a schedule.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `schedule_id` | string | Yes | Schedule ID |

**Example prompt:**
> "Delete the old release test schedule"

---

## Example Conversations

### Basic Load Test

**You:** Run a load test against https://httpbin.org/get with 50 requests

**Claude:** I'll run that load test for you.
[Uses run_api_test tool]

Test started successfully!
- Run ID: abc12345-...
- Status: running

Would you like me to check the status when it completes?

---

### Checking Results

**You:** Yes, check the results

**Claude:** [Uses get_test_status tool]

Test completed!
- Status: COMPLETED
- Result: PASSED
- Progress: 50/50 requests

Metrics:
- Throughput: 45.2 req/s
- P50 Latency: 120.5ms
- P95 Latency: 245.3ms
- P99 Latency: 312.1ms
- Error Rate: 0.0%

---

### Performance Analysis

**You:** Compare that to yesterday's results for the same test

**Claude:** [Uses get_test_results tool with test_name]

Here are the recent runs for this test:

| Run | Time | P95 Latency | Error Rate |
|-----|------|-------------|------------|
| Today | 245ms | 0% |
| Yesterday | 312ms | 0.5% |

Today's test shows improved latency (21% faster) and no errors compared to yesterday.

---

### Automated Testing

**You:** Set up a test that runs against our staging API and fails if P95 latency exceeds 200ms

**Claude:** [Uses create_test_spec tool]

Here's your test specification:

```json
{
  "name": "Staging API Latency Check",
  "url": "https://staging.api.example.com/health",
  "method": "GET",
  "total_requests": 100,
  "concurrency": 10,
  "thresholds": {
    "max_latency_p95_ms": 200
  }
}
```

Save this to a file and run with: `atm run staging-test.json --wait`

Want me to run this test now?

## Tips

### 1. Naming Tests Consistently

Use consistent names to track tests over time:
- "Production API - Daily Check"
- "Staging - Login Flow"
- "Dev - New Feature Test"

### 2. Setting Appropriate Thresholds

Ask Claude to help set thresholds based on your SLAs:
> "What thresholds should I set if my SLA requires 99.9% of requests under 500ms?"

### 3. Interpreting Results

Ask for analysis:
> "Is this error rate concerning for a production API?"
> "How does this latency compare to typical web APIs?"

### 4. Troubleshooting

If tests fail, ask for debugging help:
> "Why did this test fail? Show me the error details"
> "What could cause connection errors in these results?"

## Environment Variables

Configure the MCP server behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `ATM_API_URL` | http://localhost:8000 | API server URL |
| `ATM_API_KEY` | (none) | API authentication key |
| `ATM_DATA_DIR` | ./data | Data directory for storage |
| `ATM_STORAGE_TYPE` | sqlite | Storage backend (sqlite or json) |

## Troubleshooting

### "Connection refused" errors

Make sure the API server is running:
```bash
uvicorn api.main:app --reload
```

### Tools not appearing

1. Check MCP server config path is correct
2. Verify Python environment has dependencies installed
3. Check Claude Desktop logs for errors

### Authentication errors

Set the API key in MCP server environment:
```json
"env": {
  "ATM_API_KEY": "your-api-key"
}
```
