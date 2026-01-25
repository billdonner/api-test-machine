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


async def main() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
