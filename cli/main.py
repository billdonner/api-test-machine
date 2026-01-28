"""Typer CLI for API Test Machine."""

import json
import sys
import time
from pathlib import Path
from typing import Annotated, Optional
from uuid import UUID

import httpx
import typer
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from cli.config import Config

app = typer.Typer(
    name="atm",
    help="API Test Machine - REST API load testing CLI",
    no_args_is_help=True,
)

console = Console()
error_console = Console(stderr=True)


def get_config() -> Config:
    """Get CLI configuration."""
    return Config.from_env()


def api_request(
    method: str,
    path: str,
    json_data: dict | None = None,
) -> httpx.Response:
    """Make an API request.

    Args:
        method: HTTP method
        path: API path
        json_data: Optional JSON body

    Returns:
        httpx Response

    Raises:
        typer.Exit: On connection errors
    """
    config = get_config()
    url = config.get_api_endpoint(path)
    headers = config.get_headers()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
            )
            return response
    except httpx.ConnectError:
        error_console.print(f"[red]Error:[/red] Cannot connect to API at {config.api_url}")
        error_console.print("Make sure the API server is running.")
        raise typer.Exit(1)
    except httpx.TimeoutException:
        error_console.print("[red]Error:[/red] Request timed out")
        raise typer.Exit(1)


def print_run_detail(data: dict) -> None:
    """Print detailed run information."""
    console.print()
    console.print(f"[bold]Run ID:[/bold] {data['id']}")
    console.print(f"[bold]Name:[/bold] {data['spec']['name']}")

    status = data["status"]
    status_color = {
        "pending": "yellow",
        "running": "blue",
        "completed": "green",
        "cancelled": "yellow",
        "failed": "red",
    }.get(status, "white")
    console.print(f"[bold]Status:[/bold] [{status_color}]{status}[/{status_color}]")

    if data.get("started_at"):
        console.print(f"[bold]Started:[/bold] {data['started_at']}")
    if data.get("completed_at"):
        console.print(f"[bold]Completed:[/bold] {data['completed_at']}")

    # Progress
    total = data["spec"]["total_requests"]
    completed = data.get("requests_completed", 0)
    console.print(f"[bold]Progress:[/bold] {completed}/{total} requests")

    # Pass/fail
    if data.get("passed") is not None:
        if data["passed"]:
            console.print("[bold]Result:[/bold] [green]PASSED[/green]")
        else:
            console.print("[bold]Result:[/bold] [red]FAILED[/red]")
            if data.get("failure_reasons"):
                console.print("[bold]Failure Reasons:[/bold]")
                for reason in data["failure_reasons"]:
                    console.print(f"  - {reason}")

    # Metrics
    metrics = data.get("metrics", {})
    if metrics.get("total_requests", 0) > 0:
        console.print()
        console.print("[bold]Metrics:[/bold]")

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="dim")
        table.add_column("Value")

        if metrics.get("requests_per_second"):
            table.add_row("Throughput", f"{metrics['requests_per_second']:.1f} req/s")
        if metrics.get("duration_seconds"):
            table.add_row("Duration", f"{metrics['duration_seconds']:.2f}s")
        table.add_row("Total Requests", str(metrics.get("total_requests", 0)))
        table.add_row("Successful", str(metrics.get("successful_requests", 0)))
        table.add_row("Failed", str(metrics.get("failed_requests", 0)))

        if metrics.get("error_rate") is not None:
            table.add_row("Error Rate", f"{metrics['error_rate']:.1%}")

        console.print(table)

        # Latency percentiles
        if metrics.get("latency_p50_ms"):
            console.print()
            console.print("[bold]Latency Percentiles:[/bold]")
            lat_table = Table(show_header=False, box=None)
            lat_table.add_column("Percentile", style="dim")
            lat_table.add_column("Value")

            if metrics.get("latency_min_ms"):
                lat_table.add_row("Min", f"{metrics['latency_min_ms']:.1f}ms")
            if metrics.get("latency_p50_ms"):
                lat_table.add_row("P50", f"{metrics['latency_p50_ms']:.1f}ms")
            if metrics.get("latency_p90_ms"):
                lat_table.add_row("P90", f"{metrics['latency_p90_ms']:.1f}ms")
            if metrics.get("latency_p95_ms"):
                lat_table.add_row("P95", f"{metrics['latency_p95_ms']:.1f}ms")
            if metrics.get("latency_p99_ms"):
                lat_table.add_row("P99", f"{metrics['latency_p99_ms']:.1f}ms")
            if metrics.get("latency_max_ms"):
                lat_table.add_row("Max", f"{metrics['latency_max_ms']:.1f}ms")

            console.print(lat_table)

    if data.get("error_message"):
        console.print()
        console.print(f"[bold red]Error:[/bold red] {data['error_message']}")


@app.command()
def run(
    spec_file: Annotated[
        Path,
        typer.Argument(
            help="Path to test spec JSON file",
            exists=True,
            readable=True,
        ),
    ],
    wait: Annotated[
        bool,
        typer.Option("--wait", "-w", help="Wait for run to complete"),
    ] = False,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Save results to JSON file"),
    ] = None,
) -> None:
    """Run a load test from a spec file."""
    # Load spec file
    try:
        with open(spec_file) as f:
            spec = json.load(f)
    except json.JSONDecodeError as e:
        error_console.print(f"[red]Error:[/red] Invalid JSON in spec file: {e}")
        raise typer.Exit(1)

    # Start the run
    response = api_request("POST", "/api/v1/runs", {"spec": spec})

    if response.status_code == 401:
        error_console.print("[red]Error:[/red] Authentication failed. Check ATM_API_KEY.")
        raise typer.Exit(1)

    if response.status_code != 202:
        error_console.print(f"[red]Error:[/red] Failed to start run: {response.text}")
        raise typer.Exit(1)

    data = response.json()
    run_id = data["id"]
    console.print(f"[green]Run started:[/green] {run_id}")

    if not wait:
        console.print(f"Use [bold]atm status {run_id}[/bold] to check progress.")
        return

    # Wait for completion
    console.print("Waiting for completion...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running...", total=None)

        while True:
            response = api_request("GET", f"/api/v1/runs/{run_id}")
            if response.status_code != 200:
                error_console.print(f"[red]Error:[/red] Failed to get status: {response.text}")
                raise typer.Exit(1)

            data = response.json()
            status = data["status"]
            completed = data.get("requests_completed", 0)
            total = data["spec"]["total_requests"]

            progress.update(task, description=f"Running... {completed}/{total} requests")

            if status in ("completed", "cancelled", "failed"):
                break

            time.sleep(1)

    # Print results
    print_run_detail(data)

    # Save to file if requested
    if output:
        with open(output, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"\nResults saved to [bold]{output}[/bold]")

    # Exit with error if failed
    if data.get("passed") is False or status == "failed":
        raise typer.Exit(1)


@app.command()
def status(
    run_id: Annotated[
        str,
        typer.Argument(help="Run ID to check"),
    ],
) -> None:
    """Get the status of a test run."""
    response = api_request("GET", f"/api/v1/runs/{run_id}")

    if response.status_code == 401:
        error_console.print("[red]Error:[/red] Authentication failed. Check ATM_API_KEY.")
        raise typer.Exit(1)

    if response.status_code == 404:
        error_console.print(f"[red]Error:[/red] Run {run_id} not found")
        raise typer.Exit(1)

    if response.status_code != 200:
        error_console.print(f"[red]Error:[/red] Failed to get status: {response.text}")
        raise typer.Exit(1)

    print_run_detail(response.json())


@app.command()
def cancel(
    run_id: Annotated[
        str,
        typer.Argument(help="Run ID to cancel"),
    ],
) -> None:
    """Cancel a running test."""
    response = api_request("POST", f"/api/v1/runs/{run_id}/cancel")

    if response.status_code == 401:
        error_console.print("[red]Error:[/red] Authentication failed. Check ATM_API_KEY.")
        raise typer.Exit(1)

    if response.status_code == 404:
        error_console.print(f"[red]Error:[/red] Run {run_id} not found")
        raise typer.Exit(1)

    data = response.json()
    console.print(f"[yellow]{data['message']}[/yellow]")


@app.command("list")
def list_runs(
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of runs to show"),
    ] = 10,
    status_filter: Annotated[
        Optional[str],
        typer.Option("--status", "-s", help="Filter by status"),
    ] = None,
) -> None:
    """List recent test runs."""
    params = f"?limit={limit}"
    if status_filter:
        params += f"&status={status_filter}"

    response = api_request("GET", f"/api/v1/runs{params}")

    if response.status_code == 401:
        error_console.print("[red]Error:[/red] Authentication failed. Check ATM_API_KEY.")
        raise typer.Exit(1)

    if response.status_code != 200:
        error_console.print(f"[red]Error:[/red] Failed to list runs: {response.text}")
        raise typer.Exit(1)

    data = response.json()
    runs = data["runs"]

    if not runs:
        console.print("[dim]No runs found[/dim]")
        return

    table = Table(title=f"Recent Runs ({data['total']} total)")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Progress")
    table.add_column("Result")

    for run in runs:
        status = run["status"]
        status_color = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "cancelled": "yellow",
            "failed": "red",
        }.get(status, "white")

        progress = f"{run['requests_completed']}/{run['total_requests']}"

        result = ""
        if run.get("passed") is True:
            result = "[green]PASS[/green]"
        elif run.get("passed") is False:
            result = "[red]FAIL[/red]"

        # Truncate ID for display
        short_id = str(run["id"])[:8] + "..."

        table.add_row(
            short_id,
            run["name"],
            f"[{status_color}]{status}[/{status_color}]",
            progress,
            result,
        )

    console.print(table)


@app.command()
def report(
    output: Annotated[
        Path,
        typer.Argument(help="Output PDF file path"),
    ],
    enabled_only: Annotated[
        bool,
        typer.Option("--enabled-only", "-e", help="Only include enabled tests"),
    ] = False,
) -> None:
    """Generate a PDF report of all test configurations."""
    params = f"?enabled_only={'true' if enabled_only else 'false'}"

    with console.status("Generating report..."):
        response = api_request("GET", f"/api/v1/tests/report{params}")

    if response.status_code == 401:
        error_console.print("[red]Error:[/red] Authentication failed. Check ATM_API_KEY.")
        raise typer.Exit(1)

    if response.status_code != 200:
        error_console.print(f"[red]Error:[/red] Failed to generate report: {response.text}")
        raise typer.Exit(1)

    # Write PDF to file
    with open(output, "wb") as f:
        f.write(response.content)

    console.print(f"[green]Report saved to:[/green] {output}")


if __name__ == "__main__":
    app()
