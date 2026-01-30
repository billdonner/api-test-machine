"""MCP server for LLM agent integration."""

import json
import os
from typing import Any
from uuid import UUID

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Server configuration
API_URL = os.environ.get("ATM_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("ATM_API_KEY")

# Create MCP server
server = Server("api-test-machine")


def get_headers() -> dict[str, str]:
    """Get HTTP headers for API requests."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def api_request(method: str, path: str, json_data: dict | None = None) -> dict:
    """Make an API request to the Control API.

    Args:
        method: HTTP method
        path: API path
        json_data: Optional JSON body

    Returns:
        Response data as dict
    """
    url = f"{API_URL.rstrip('/')}/{path.lstrip('/')}"

    with httpx.Client(timeout=60.0) as client:
        response = client.request(
            method=method,
            url=url,
            headers=get_headers(),
            json=json_data,
        )

        if response.status_code >= 400:
            return {
                "error": True,
                "status_code": response.status_code,
                "message": response.text,
            }

        return response.json()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="run_api_test",
            description="Execute a load test against an API endpoint",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the test run",
                    },
                    "url": {
                        "type": "string",
                        "description": "Target URL to test",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        "default": "GET",
                        "description": "HTTP method",
                    },
                    "total_requests": {
                        "type": "integer",
                        "default": 100,
                        "description": "Total number of requests to make",
                    },
                    "concurrency": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of concurrent requests",
                    },
                    "requests_per_second": {
                        "type": "number",
                        "description": "Rate limit (requests per second)",
                    },
                    "headers": {
                        "type": "object",
                        "description": "HTTP headers to include",
                    },
                    "body": {
                        "type": "string",
                        "description": "Request body (JSON string)",
                    },
                },
                "required": ["name", "url"],
            },
        ),
        Tool(
            name="get_test_status",
            description="Get the status and results of a test run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "ID of the test run",
                    },
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="cancel_test",
            description="Cancel a running test",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "ID of the test run to cancel",
                    },
                },
                "required": ["run_id"],
            },
        ),
        Tool(
            name="list_recent_tests",
            description="List recent test runs",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of runs to return",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "running", "completed", "cancelled", "failed"],
                        "description": "Filter by status",
                    },
                },
            },
        ),
        Tool(
            name="create_test_spec",
            description="Generate a reusable test specification JSON",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the test",
                    },
                    "url": {
                        "type": "string",
                        "description": "Target URL",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        "default": "GET",
                    },
                    "total_requests": {
                        "type": "integer",
                        "default": 100,
                    },
                    "concurrency": {
                        "type": "integer",
                        "default": 10,
                    },
                    "requests_per_second": {
                        "type": "number",
                    },
                    "headers": {
                        "type": "object",
                    },
                    "body": {
                        "type": "object",
                    },
                    "timeout_seconds": {
                        "type": "number",
                        "default": 30,
                    },
                    "max_latency_p95_ms": {
                        "type": "number",
                        "description": "P95 latency threshold in ms",
                    },
                    "max_error_rate": {
                        "type": "number",
                        "description": "Maximum error rate (0-1)",
                    },
                },
                "required": ["name", "url"],
            },
        ),
        Tool(
            name="rerun_test",
            description="Re-run an existing test by name. Finds the most recent run with that name and creates a new run with the same configuration.",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_name": {
                        "type": "string",
                        "description": "Name of the test to re-run (e.g., 'San Francisco Weather')",
                    },
                },
                "required": ["test_name"],
            },
        ),
        Tool(
            name="get_test_results",
            description="Get test results. Either provide a run_id for a specific run, or a test_name to get all runs with that name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "ID of a specific test run",
                    },
                    "test_name": {
                        "type": "string",
                        "description": "Name of the test to get all runs for",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of runs to return (when using test_name)",
                    },
                },
            },
        ),
        # Schedule tools
        Tool(
            name="create_schedule",
            description="Create a new schedule to run tests automatically at specified intervals",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the schedule",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description",
                    },
                    "test_name": {
                        "type": "string",
                        "description": "Name of the test configuration to run",
                    },
                    "trigger_type": {
                        "type": "string",
                        "enum": ["interval", "cron", "date"],
                        "description": "Type of schedule trigger",
                    },
                    "interval_hours": {
                        "type": "integer",
                        "description": "Hours between runs (for interval trigger)",
                    },
                    "interval_minutes": {
                        "type": "integer",
                        "description": "Minutes between runs (for interval trigger)",
                    },
                    "interval_seconds": {
                        "type": "integer",
                        "description": "Seconds between runs (for interval trigger)",
                    },
                    "cron_expression": {
                        "type": "string",
                        "description": "Cron expression: 'minute hour day month day_of_week' (for cron trigger)",
                    },
                    "run_date": {
                        "type": "string",
                        "description": "ISO 8601 date/time for one-time run (for date trigger)",
                    },
                    "max_runs": {
                        "type": "integer",
                        "description": "Maximum number of runs (optional, unlimited if not set)",
                    },
                    "enabled": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether the schedule is enabled",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorizing the schedule",
                    },
                },
                "required": ["name", "test_name", "trigger_type"],
            },
        ),
        Tool(
            name="list_schedules",
            description="List all schedules",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "Filter by enabled status",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Filter by tag",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 50,
                        "description": "Maximum number of schedules to return",
                    },
                },
            },
        ),
        Tool(
            name="get_schedule",
            description="Get details of a specific schedule",
            inputSchema={
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "ID of the schedule",
                    },
                },
                "required": ["schedule_id"],
            },
        ),
        Tool(
            name="pause_schedule",
            description="Pause a schedule to temporarily stop it from running",
            inputSchema={
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "ID of the schedule to pause",
                    },
                },
                "required": ["schedule_id"],
            },
        ),
        Tool(
            name="resume_schedule",
            description="Resume a paused schedule",
            inputSchema={
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "ID of the schedule to resume",
                    },
                },
                "required": ["schedule_id"],
            },
        ),
        Tool(
            name="delete_schedule",
            description="Delete a schedule permanently",
            inputSchema={
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "ID of the schedule to delete",
                    },
                },
                "required": ["schedule_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if name == "run_api_test":
        return await run_api_test(arguments)
    elif name == "get_test_status":
        return await get_test_status(arguments)
    elif name == "cancel_test":
        return await cancel_test(arguments)
    elif name == "list_recent_tests":
        return await list_recent_tests(arguments)
    elif name == "create_test_spec":
        return await create_test_spec(arguments)
    elif name == "rerun_test":
        return await rerun_test(arguments)
    elif name == "get_test_results":
        return await get_test_results(arguments)
    # Schedule tools
    elif name == "create_schedule":
        return await create_schedule(arguments)
    elif name == "list_schedules":
        return await list_schedules(arguments)
    elif name == "get_schedule":
        return await get_schedule(arguments)
    elif name == "pause_schedule":
        return await pause_schedule(arguments)
    elif name == "resume_schedule":
        return await resume_schedule(arguments)
    elif name == "delete_schedule":
        return await delete_schedule(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def run_api_test(args: dict[str, Any]) -> list[TextContent]:
    """Execute a load test."""
    spec = {
        "name": args["name"],
        "url": args["url"],
        "method": args.get("method", "GET"),
        "total_requests": args.get("total_requests", 100),
        "concurrency": args.get("concurrency", 10),
    }

    if args.get("requests_per_second"):
        spec["requests_per_second"] = args["requests_per_second"]
    if args.get("headers"):
        spec["headers"] = args["headers"]
    if args.get("body"):
        spec["body"] = json.loads(args["body"]) if isinstance(args["body"], str) else args["body"]

    result = api_request("POST", "/api/v1/runs", {"spec": spec})

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    return [TextContent(
        type="text",
        text=f"Test started successfully!\n"
             f"Run ID: {result['id']}\n"
             f"Status: {result['status']}\n"
             f"Use get_test_status to check progress.",
    )]


async def get_test_status(args: dict[str, Any]) -> list[TextContent]:
    """Get status of a test run."""
    run_id = args["run_id"]
    result = api_request("GET", f"/api/v1/runs/{run_id}")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    # Format output
    output = [
        f"Run ID: {result['id']}",
        f"Name: {result['spec']['name']}",
        f"Status: {result['status']}",
        f"Progress: {result['requests_completed']}/{result['spec']['total_requests']} requests",
    ]

    if result.get("passed") is not None:
        output.append(f"Result: {'PASSED' if result['passed'] else 'FAILED'}")

    if result.get("failure_reasons"):
        output.append("Failure Reasons:")
        for reason in result["failure_reasons"]:
            output.append(f"  - {reason}")

    metrics = result.get("metrics", {})
    if metrics.get("total_requests", 0) > 0:
        output.append("\nMetrics:")
        if metrics.get("requests_per_second"):
            output.append(f"  Throughput: {metrics['requests_per_second']:.1f} req/s")
        if metrics.get("latency_p50_ms"):
            output.append(f"  P50 Latency: {metrics['latency_p50_ms']:.1f}ms")
        if metrics.get("latency_p95_ms"):
            output.append(f"  P95 Latency: {metrics['latency_p95_ms']:.1f}ms")
        if metrics.get("latency_p99_ms"):
            output.append(f"  P99 Latency: {metrics['latency_p99_ms']:.1f}ms")
        if metrics.get("error_rate") is not None:
            output.append(f"  Error Rate: {metrics['error_rate']:.1%}")

    return [TextContent(type="text", text="\n".join(output))]


async def cancel_test(args: dict[str, Any]) -> list[TextContent]:
    """Cancel a running test."""
    run_id = args["run_id"]
    result = api_request("POST", f"/api/v1/runs/{run_id}/cancel")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    return [TextContent(
        type="text",
        text=f"Cancellation requested for run {run_id}\n"
             f"Status: {result['status']}\n"
             f"Message: {result['message']}",
    )]


async def list_recent_tests(args: dict[str, Any]) -> list[TextContent]:
    """List recent test runs."""
    limit = args.get("limit", 10)
    params = f"?limit={limit}"
    if args.get("status"):
        params += f"&status={args['status']}"

    result = api_request("GET", f"/api/v1/runs{params}")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    runs = result.get("runs", [])
    if not runs:
        return [TextContent(type="text", text="No test runs found.")]

    output = [f"Recent Test Runs ({result['total']} total):", ""]

    for run in runs:
        status_icon = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✅",
            "cancelled": "⚠️",
            "failed": "❌",
        }.get(run["status"], "❓")

        result_str = ""
        if run.get("passed") is True:
            result_str = " [PASS]"
        elif run.get("passed") is False:
            result_str = " [FAIL]"

        output.append(
            f"{status_icon} {run['name']}{result_str}\n"
            f"   ID: {run['id'][:8]}...\n"
            f"   Progress: {run['requests_completed']}/{run['total_requests']}"
        )

    return [TextContent(type="text", text="\n".join(output))]


async def create_test_spec(args: dict[str, Any]) -> list[TextContent]:
    """Generate a test spec JSON."""
    spec = {
        "name": args["name"],
        "url": args["url"],
        "method": args.get("method", "GET"),
        "total_requests": args.get("total_requests", 100),
        "concurrency": args.get("concurrency", 10),
        "timeout_seconds": args.get("timeout_seconds", 30),
        "headers": args.get("headers", {}),
        "thresholds": {},
        "expected_status_codes": [200, 201, 204],
    }

    if args.get("requests_per_second"):
        spec["requests_per_second"] = args["requests_per_second"]
    if args.get("body"):
        spec["body"] = args["body"]
    if args.get("max_latency_p95_ms"):
        spec["thresholds"]["max_latency_p95_ms"] = args["max_latency_p95_ms"]
    if args.get("max_error_rate"):
        spec["thresholds"]["max_error_rate"] = args["max_error_rate"]

    return [TextContent(
        type="text",
        text=f"Generated test specification:\n\n```json\n{json.dumps(spec, indent=2)}\n```\n\n"
             f"Save this to a file (e.g., test-spec.json) and use with:\n"
             f"  atm run test-spec.json --wait",
    )]


async def rerun_test(args: dict[str, Any]) -> list[TextContent]:
    """Re-run a test by finding the most recent run with the given name."""
    test_name = args["test_name"]

    # Get all runs and find the most recent one with this name
    result = api_request("GET", "/api/v1/runs?limit=100")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    runs = result.get("runs", [])
    matching_run = None
    for run in runs:
        if run["name"].lower() == test_name.lower():
            matching_run = run
            break

    if not matching_run:
        return [TextContent(
            type="text",
            text=f"No test found with name '{test_name}'.\n\n"
                 f"Available tests:\n" +
                 "\n".join(f"  - {r['name']}" for r in {r['name']: r for r in runs}.values())
        )]

    # Get full run details to get the spec
    run_detail = api_request("GET", f"/api/v1/runs/{matching_run['id']}")
    if run_detail.get("error"):
        return [TextContent(type="text", text=f"Error loading test details: {run_detail.get('message')}")]

    # Create new run with the same spec
    new_run = api_request("POST", "/api/v1/runs", {"spec": run_detail["spec"]})

    if new_run.get("error"):
        return [TextContent(type="text", text=f"Error starting test: {new_run.get('message')}")]

    return [TextContent(
        type="text",
        text=f"Test '{test_name}' started!\n"
             f"New Run ID: {new_run['id']}\n"
             f"Status: {new_run['status']}\n"
             f"Configuration:\n"
             f"  URL: {run_detail['spec']['url']}\n"
             f"  Method: {run_detail['spec']['method']}\n"
             f"  Requests: {run_detail['spec']['total_requests']}\n"
             f"  Concurrency: {run_detail['spec']['concurrency']}\n\n"
             f"Use get_test_status or get_test_results to check progress.",
    )]


async def get_test_results(args: dict[str, Any]) -> list[TextContent]:
    """Get test results for a specific run or all runs matching a test name."""
    run_id = args.get("run_id")
    test_name = args.get("test_name")
    limit = args.get("limit", 10)

    if not run_id and not test_name:
        return [TextContent(
            type="text",
            text="Please provide either run_id or test_name."
        )]

    if run_id:
        # Get single run
        result = api_request("GET", f"/api/v1/runs/{run_id}")

        if result.get("error"):
            return [TextContent(type="text", text=f"Error: {result.get('message')}")]

        return [TextContent(type="text", text=format_run_result(result))]

    # Get all runs matching test_name
    all_runs = api_request("GET", f"/api/v1/runs?limit=200")

    if all_runs.get("error"):
        return [TextContent(type="text", text=f"Error: {all_runs.get('message')}")]

    matching_runs = [
        r for r in all_runs.get("runs", [])
        if r["name"].lower() == test_name.lower()
    ][:limit]

    if not matching_runs:
        return [TextContent(
            type="text",
            text=f"No runs found for test '{test_name}'."
        )]

    output = [f"Results for '{test_name}' ({len(matching_runs)} runs):", ""]

    for run in matching_runs:
        # Get full details for each run
        detail = api_request("GET", f"/api/v1/runs/{run['id']}")
        if not detail.get("error"):
            output.append(format_run_result(detail, compact=True))
            output.append("")

    return [TextContent(type="text", text="\n".join(output))]


def format_run_result(result: dict, compact: bool = False) -> str:
    """Format a run result for display."""
    status_icon = {
        "pending": "⏳",
        "running": "🔄",
        "completed": "✅",
        "cancelled": "⚠️",
        "failed": "❌",
    }.get(result["status"], "❓")

    pass_fail = ""
    if result.get("passed") is True:
        pass_fail = " ✅ PASSED"
    elif result.get("passed") is False:
        pass_fail = " ❌ FAILED"

    if compact:
        # Compact format for list view
        metrics = result.get("metrics", {})
        latency = f"P95: {metrics.get('latency_p95_ms', 0):.0f}ms" if metrics.get('latency_p95_ms') else ""
        rps = f"{metrics.get('requests_per_second', 0):.1f} req/s" if metrics.get('requests_per_second') else ""

        return (
            f"{status_icon} Run {result['id'][:8]}...{pass_fail}\n"
            f"   Progress: {result['requests_completed']}/{result['spec']['total_requests']} | "
            f"{latency} | {rps}"
        )

    # Full format
    output = [
        f"{status_icon} {result['spec']['name']}{pass_fail}",
        f"Run ID: {result['id']}",
        f"Status: {result['status']}",
        f"Progress: {result['requests_completed']}/{result['spec']['total_requests']} requests",
    ]

    if result.get("started_at"):
        output.append(f"Started: {result['started_at']}")
    if result.get("completed_at"):
        output.append(f"Completed: {result['completed_at']}")

    if result.get("failure_reasons"):
        output.append("\nFailure Reasons:")
        for reason in result["failure_reasons"]:
            output.append(f"  - {reason}")

    metrics = result.get("metrics", {})
    if metrics.get("total_requests", 0) > 0:
        output.append("\nMetrics:")
        output.append(f"  Total Requests: {metrics.get('total_requests', 0)}")
        output.append(f"  Successful: {metrics.get('successful_requests', 0)}")
        output.append(f"  Failed: {metrics.get('failed_requests', 0)}")
        if metrics.get("requests_per_second"):
            output.append(f"  Throughput: {metrics['requests_per_second']:.2f} req/s")
        if metrics.get("latency_min_ms"):
            output.append(f"  Latency Min: {metrics['latency_min_ms']:.1f}ms")
        if metrics.get("latency_mean_ms"):
            output.append(f"  Latency Mean: {metrics['latency_mean_ms']:.1f}ms")
        if metrics.get("latency_p50_ms"):
            output.append(f"  Latency P50: {metrics['latency_p50_ms']:.1f}ms")
        if metrics.get("latency_p95_ms"):
            output.append(f"  Latency P95: {metrics['latency_p95_ms']:.1f}ms")
        if metrics.get("latency_p99_ms"):
            output.append(f"  Latency P99: {metrics['latency_p99_ms']:.1f}ms")
        if metrics.get("latency_max_ms"):
            output.append(f"  Latency Max: {metrics['latency_max_ms']:.1f}ms")
        if metrics.get("error_rate") is not None:
            output.append(f"  Error Rate: {metrics['error_rate']:.1%}")

        if metrics.get("status_code_counts"):
            output.append("  Status Codes:")
            for code, count in metrics["status_code_counts"].items():
                output.append(f"    {code}: {count}")

    return "\n".join(output)


# Schedule tool implementations

async def create_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Create a new schedule."""
    trigger_type = args["trigger_type"]

    # Build trigger based on type
    if trigger_type == "interval":
        trigger: dict[str, Any] = {"type": "interval"}
        if args.get("interval_hours"):
            trigger["hours"] = args["interval_hours"]
        if args.get("interval_minutes"):
            trigger["minutes"] = args["interval_minutes"]
        if args.get("interval_seconds"):
            trigger["seconds"] = args["interval_seconds"]
        # Default to 1 hour if no interval specified
        if len(trigger) == 1:
            trigger["hours"] = 1

    elif trigger_type == "cron":
        cron_expr = args.get("cron_expression", "* * * * *")
        parts = cron_expr.split()
        if len(parts) != 5:
            return [TextContent(
                type="text",
                text="Invalid cron expression. Format: 'minute hour day month day_of_week'"
            )]
        trigger = {
            "type": "cron",
            "minute": parts[0],
            "hour": parts[1],
            "day": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
            "timezone": "UTC",
        }

    elif trigger_type == "date":
        run_date = args.get("run_date")
        if not run_date:
            return [TextContent(
                type="text",
                text="run_date is required for date trigger type"
            )]
        trigger = {
            "type": "date",
            "run_date": run_date,
        }
    else:
        return [TextContent(
            type="text",
            text=f"Invalid trigger_type: {trigger_type}. Use 'interval', 'cron', or 'date'"
        )]

    # Build schedule request
    schedule_data = {
        "name": args["name"],
        "test_name": args["test_name"],
        "trigger": trigger,
        "enabled": args.get("enabled", True),
        "tags": args.get("tags", []),
    }

    if args.get("description"):
        schedule_data["description"] = args["description"]
    if args.get("max_runs"):
        schedule_data["max_runs"] = args["max_runs"]

    result = api_request("POST", "/api/v1/schedules", schedule_data)

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    return [TextContent(
        type="text",
        text=f"Schedule created successfully!\n"
             f"ID: {result['id']}\n"
             f"Name: {result['name']}\n"
             f"Test: {result['test_name']}\n"
             f"Trigger: {format_trigger(result.get('trigger', {}))}\n"
             f"Enabled: {result['enabled']}\n"
             f"Next Run: {result.get('next_run_time', 'Not scheduled')}",
    )]


async def list_schedules(args: dict[str, Any]) -> list[TextContent]:
    """List all schedules."""
    params = []
    if args.get("limit"):
        params.append(f"limit={args['limit']}")
    if args.get("enabled") is not None:
        params.append(f"enabled={str(args['enabled']).lower()}")
    if args.get("tag"):
        params.append(f"tag={args['tag']}")

    query = "?" + "&".join(params) if params else ""
    result = api_request("GET", f"/api/v1/schedules{query}")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    schedules = result.get("schedules", [])
    if not schedules:
        return [TextContent(type="text", text="No schedules found.")]

    output = [f"Schedules ({result.get('total', len(schedules))} total):", ""]

    for sched in schedules:
        status_icon = "✅" if sched.get("enabled") else "⏸️"
        if sched.get("paused"):
            status_icon = "⏸️"

        output.append(
            f"{status_icon} {sched['name']}\n"
            f"   ID: {sched['id'][:8]}...\n"
            f"   Test: {sched['test_name']}\n"
            f"   Trigger: {format_trigger(sched.get('trigger', {}))}\n"
            f"   Runs: {sched.get('run_count', 0)}"
            + (f"/{sched['max_runs']}" if sched.get('max_runs') else "") +
            f"\n   Next: {sched.get('next_run_time', 'Not scheduled')}"
        )
        output.append("")

    return [TextContent(type="text", text="\n".join(output))]


async def get_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Get details of a specific schedule."""
    schedule_id = args["schedule_id"]
    result = api_request("GET", f"/api/v1/schedules/{schedule_id}")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    sched = result
    status = "Enabled" if sched.get("enabled") else "Disabled"
    if sched.get("paused"):
        status = "Paused"

    output = [
        f"Schedule: {sched['name']}",
        f"ID: {sched['id']}",
        f"Description: {sched.get('description', 'N/A')}",
        f"Test: {sched['test_name']}",
        f"Status: {status}",
        f"Trigger Type: {sched.get('trigger_type', 'unknown')}",
        f"Trigger: {format_trigger(sched.get('trigger', {}))}",
        f"Run Count: {sched.get('run_count', 0)}"
        + (f"/{sched['max_runs']}" if sched.get('max_runs') else " (unlimited)"),
        f"Next Run: {sched.get('next_run_time', 'Not scheduled')}",
        f"Created: {sched.get('created_at', 'N/A')}",
        f"Updated: {sched.get('updated_at', 'N/A')}",
    ]

    if sched.get("tags"):
        output.append(f"Tags: {', '.join(sched['tags'])}")

    return [TextContent(type="text", text="\n".join(output))]


async def pause_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Pause a schedule."""
    schedule_id = args["schedule_id"]
    result = api_request("POST", f"/api/v1/schedules/{schedule_id}/pause")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    return [TextContent(
        type="text",
        text=f"Schedule paused successfully!\n"
             f"ID: {result.get('id', schedule_id)}\n"
             f"Message: {result.get('message', 'Schedule has been paused')}",
    )]


async def resume_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Resume a paused schedule."""
    schedule_id = args["schedule_id"]
    result = api_request("POST", f"/api/v1/schedules/{schedule_id}/resume")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    return [TextContent(
        type="text",
        text=f"Schedule resumed successfully!\n"
             f"ID: {result.get('id', schedule_id)}\n"
             f"Message: {result.get('message', 'Schedule has been resumed')}",
    )]


async def delete_schedule(args: dict[str, Any]) -> list[TextContent]:
    """Delete a schedule."""
    schedule_id = args["schedule_id"]
    result = api_request("DELETE", f"/api/v1/schedules/{schedule_id}")

    if result.get("error"):
        return [TextContent(type="text", text=f"Error: {result.get('message')}")]

    return [TextContent(
        type="text",
        text=f"Schedule deleted successfully!\n"
             f"ID: {result.get('id', schedule_id)}\n"
             f"Message: {result.get('message', 'Schedule has been deleted')}",
    )]


def format_trigger(trigger: dict) -> str:
    """Format a trigger dict for display."""
    trigger_type = trigger.get("type", "unknown")

    if trigger_type == "interval":
        parts = []
        if trigger.get("days"):
            parts.append(f"{trigger['days']}d")
        if trigger.get("hours"):
            parts.append(f"{trigger['hours']}h")
        if trigger.get("minutes"):
            parts.append(f"{trigger['minutes']}m")
        if trigger.get("seconds"):
            parts.append(f"{trigger['seconds']}s")
        return f"Every {' '.join(parts)}" if parts else "Interval (not set)"

    elif trigger_type == "cron":
        minute = trigger.get("minute", "*")
        hour = trigger.get("hour", "*")
        day = trigger.get("day", "*")
        month = trigger.get("month", "*")
        dow = trigger.get("day_of_week", "*")
        return f"Cron: {minute} {hour} {day} {month} {dow}"

    elif trigger_type == "date":
        return f"One-time: {trigger.get('run_date', 'N/A')}"

    return str(trigger)


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
