# MCP Server Demo Prompts

This document demonstrates how to use the API Test Machine MCP server tools with example prompts and expected responses.

## Prerequisites

1. **API Server Running**: Start the Control API server:
   ```bash
   uvicorn api.app:create_app --factory --reload
   ```

2. **Environment Variables**: Configure MCP server connection:
   ```bash
   export ATM_API_URL="http://localhost:8000"
   export ATM_API_KEY="your-api-key"
   ```

3. **MCP Server Connected**: The MCP server must be registered with your LLM client (Claude Desktop, MCP inspector, etc.)

---

## Tool Reference

| Tool | Description |
|------|-------------|
| `run_api_test` | Execute a load test against an API endpoint |
| `get_test_status` | Get the status and results of a test run |
| `cancel_test` | Cancel a running test |
| `list_recent_tests` | List recent test runs |
| `create_test_spec` | Generate a reusable test specification JSON |

---

## Tool Demos

### 1. run_api_test

Start a load test against an API endpoint.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Name for the test run |
| `url` | string | Yes | - | Target URL to test |
| `method` | string | No | "GET" | HTTP method (GET, POST, PUT, PATCH, DELETE) |
| `total_requests` | integer | No | 100 | Total number of requests |
| `concurrency` | integer | No | 10 | Concurrent requests |
| `requests_per_second` | number | No | - | Rate limit |
| `headers` | object | No | - | HTTP headers |
| `body` | string | No | - | Request body (JSON string) |

**Example Prompt:**
> Run a quick load test against httpbin.org with 20 requests at concurrency 5

**Tool Call:**
```json
{
  "name": "run_api_test",
  "arguments": {
    "name": "HTTPBin Quick Test",
    "url": "https://httpbin.org/get",
    "total_requests": 20,
    "concurrency": 5
  }
}
```

**Expected Response:**
```
Test started successfully!
Run ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Status: running
Use get_test_status to check progress.
```

**Example with POST and headers:**
> Run a POST test against my API with authorization header

**Tool Call:**
```json
{
  "name": "run_api_test",
  "arguments": {
    "name": "Auth API Test",
    "url": "https://api.example.com/users",
    "method": "POST",
    "total_requests": 50,
    "concurrency": 10,
    "headers": {
      "Authorization": "Bearer token123",
      "Content-Type": "application/json"
    },
    "body": "{\"name\": \"Test User\", \"email\": \"test@example.com\"}"
  }
}
```

---

### 2. get_test_status

Check the progress and results of a test run.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | string | Yes | ID of the test run |

**Example Prompt:**
> What's the status of test run a1b2c3d4-e5f6-7890-abcd-ef1234567890?

**Tool Call:**
```json
{
  "name": "get_test_status",
  "arguments": {
    "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

**Expected Response (Running):**
```
Run ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Name: HTTPBin Quick Test
Status: running
Progress: 15/20 requests
```

**Expected Response (Completed - Pass):**
```
Run ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Name: HTTPBin Quick Test
Status: completed
Progress: 20/20 requests
Result: PASSED

Metrics:
  Throughput: 12.5 req/s
  P50 Latency: 85.2ms
  P95 Latency: 142.8ms
  P99 Latency: 198.3ms
  Error Rate: 0.0%
```

**Expected Response (Completed - Fail):**
```
Run ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Name: Slow API Test
Status: completed
Progress: 100/100 requests
Result: FAILED
Failure Reasons:
  - P95 latency 1523ms exceeds threshold 1000ms

Metrics:
  Throughput: 8.2 req/s
  P50 Latency: 450.1ms
  P95 Latency: 1523.4ms
  P99 Latency: 2105.7ms
  Error Rate: 2.0%
```

---

### 3. cancel_test

Stop a running test before completion.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `run_id` | string | Yes | ID of the test run to cancel |

**Example Prompt:**
> Cancel the test run a1b2c3d4-e5f6-7890-abcd-ef1234567890

**Tool Call:**
```json
{
  "name": "cancel_test",
  "arguments": {
    "run_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

**Expected Response:**
```
Cancellation requested for run a1b2c3d4-e5f6-7890-abcd-ef1234567890
Status: cancelled
Message: Test run cancelled
```

---

### 4. list_recent_tests

View recent test runs with optional filtering.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 10 | Number of runs to return |
| `status` | string | No | - | Filter by status (pending, running, completed, cancelled, failed) |

**Example Prompt:**
> Show me the last 5 test runs

**Tool Call:**
```json
{
  "name": "list_recent_tests",
  "arguments": {
    "limit": 5
  }
}
```

**Expected Response:**
```
Recent Test Runs (12 total):

✅ HTTPBin Quick Test [PASS]
   ID: a1b2c3d4...
   Progress: 20/20

❌ Slow API Test [FAIL]
   ID: b2c3d4e5...
   Progress: 100/100

⚠️ Cancelled Test
   ID: c3d4e5f6...
   Progress: 45/100

🔄 Long Running Test
   ID: d4e5f6a7...
   Progress: 230/1000

✅ Health Check [PASS]
   ID: e5f6a7b8...
   Progress: 10/10
```

**Example with status filter:**
> Show me only failed tests

**Tool Call:**
```json
{
  "name": "list_recent_tests",
  "arguments": {
    "status": "completed",
    "limit": 10
  }
}
```

---

### 5. create_test_spec

Generate a reusable test specification JSON that can be saved to a file.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Name for the test |
| `url` | string | Yes | - | Target URL |
| `method` | string | No | "GET" | HTTP method |
| `total_requests` | integer | No | 100 | Total requests |
| `concurrency` | integer | No | 10 | Concurrent requests |
| `requests_per_second` | number | No | - | Rate limit |
| `headers` | object | No | - | HTTP headers |
| `body` | object | No | - | Request body |
| `timeout_seconds` | number | No | 30 | Request timeout |
| `max_latency_p95_ms` | number | No | - | P95 latency threshold |
| `max_error_rate` | number | No | - | Maximum error rate (0-1) |

**Example Prompt:**
> Create a test spec for our production API health endpoint with strict thresholds

**Tool Call:**
```json
{
  "name": "create_test_spec",
  "arguments": {
    "name": "Production Health Check",
    "url": "https://api.myapp.com/health",
    "total_requests": 100,
    "concurrency": 20,
    "requests_per_second": 50,
    "max_latency_p95_ms": 200,
    "max_error_rate": 0.01
  }
}
```

**Expected Response:**
```
Generated test specification:

```json
{
  "name": "Production Health Check",
  "url": "https://api.myapp.com/health",
  "method": "GET",
  "total_requests": 100,
  "concurrency": 20,
  "timeout_seconds": 30,
  "headers": {},
  "thresholds": {
    "max_latency_p95_ms": 200,
    "max_error_rate": 0.01
  },
  "expected_status_codes": [200, 201, 204],
  "requests_per_second": 50
}
```

Save this to a file (e.g., test-spec.json) and use with:
  atm run test-spec.json --wait
```

---

## Example Workflows

### Workflow 1: Quick Health Check

Run a simple health check to verify an API is responsive.

**Prompt Sequence:**

1. > Run a quick health check on https://httpbin.org/get with just 10 requests

2. > What's the status of that test?

**What happens:**
- `run_api_test` starts a minimal load test (10 requests, default concurrency)
- `get_test_status` retrieves the results showing latency and success rate

---

### Workflow 2: Monitor a Long-Running Test

Start a larger test and poll for completion.

**Prompt Sequence:**

1. > Run a stress test against https://api.example.com/data with 1000 requests at 50 concurrency

2. > Check the progress

3. > (repeat until done) Check again

4. > Show me the final results

**What happens:**
- `run_api_test` starts the test and returns immediately with the run ID
- `get_test_status` shows progress (e.g., 250/1000 requests)
- Continue polling until status shows "completed"
- Final call shows full metrics and pass/fail result

---

### Workflow 3: Generate, Review, and Run a Test Spec

Create a reusable test configuration for CI/CD integration.

**Prompt Sequence:**

1. > Create a test spec for our user API that POST's to /api/users with a JSON body, 500 requests, and p95 latency under 500ms

2. > (User saves the JSON to a file)

3. > Now run that spec using the CLI: `atm run user-api-test.json --wait`

**What happens:**
- `create_test_spec` generates a complete JSON specification
- User saves it to a file in their project
- Test can be run repeatedly via CLI or scheduled in CI/CD

---

### Workflow 4: Investigate and Cancel a Slow Test

Handle a test that's taking too long.

**Prompt Sequence:**

1. > List all running tests

2. > That test d4e5f6a7... is taking forever. What's its status?

3. > Cancel it

**What happens:**
- `list_recent_tests` with status filter shows active tests
- `get_test_status` provides details on the problematic test
- `cancel_test` stops the test gracefully

---

### Workflow 5: Compare Before/After Performance

Test an API before and after a deployment.

**Prompt Sequence:**

1. > Run a baseline test called "Pre-Deploy" against https://api.example.com/compute with 200 requests

2. > (User deploys new code)

3. > Run the same test but call it "Post-Deploy"

4. > Show me all completed tests

5. > Get the status of the Pre-Deploy test

6. > Get the status of the Post-Deploy test

**What happens:**
- Two identical tests with different names
- `list_recent_tests` shows both
- Compare metrics between the two runs to identify regressions

---

## Error Handling

### API Server Not Running
```
Error: Connection refused - http://localhost:8000/api/v1/runs
```
**Fix:** Start the API server with `uvicorn api.app:create_app --factory`

### Invalid API Key
```
Error: {"detail": "Invalid API key"}
```
**Fix:** Set the correct `ATM_API_KEY` environment variable

### Test Not Found
```
Error: {"detail": "Run not found"}
```
**Fix:** Verify the run ID is correct using `list_recent_tests`

### Target URL Unreachable
The test will still complete but with high error rates:
```
Metrics:
  Error Rate: 100.0%
Result: FAILED
Failure Reasons:
  - Error rate 100.0% exceeds threshold 5.0%
```

---

## Tips for Effective Prompts

1. **Be specific about scale**: "100 requests at 10 concurrency" is clearer than "a small test"

2. **Name tests descriptively**: Good names like "Prod Health Check" or "Auth API Stress Test" make history easier to navigate

3. **Set appropriate thresholds**: Use `create_test_spec` to generate specs with pass/fail criteria

4. **Use rate limiting for production**: Set `requests_per_second` to avoid overwhelming production systems

5. **Check status for long tests**: Large tests (1000+ requests) benefit from periodic status checks
