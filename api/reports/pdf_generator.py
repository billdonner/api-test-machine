"""PDF report generation for test configurations."""

from datetime import datetime, timezone

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def derive_description(name: str, description: str | None) -> str:
    """Return description or derive from test name.

    Args:
        name: The test name
        description: The existing description (may be None or empty)

    Returns:
        The description if provided, otherwise a derived description
    """
    if description:
        return description
    # Clean up name: replace hyphens/underscores with spaces
    clean_name = name.replace("-", " ").replace("_", " ")
    return f"Load test for {clean_name}"


class TestReportPDF(FPDF):
    """Custom PDF class for test configuration reports."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Add page header."""
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "API Test Machine - Test Configuration Report", align="C")
        self.ln(15)

    def footer(self):
        """Add page footer with page number."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def add_summary_page(self, configs: list[dict]) -> None:
        """Add the summary page with test counts."""
        self.add_page()

        # Title
        self.set_font("Helvetica", "B", 20)
        self.cell(0, 15, "Test Configuration Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(5)

        # Generated timestamp
        self.set_font("Helvetica", "", 10)
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        self.cell(0, 8, f"Generated: {timestamp}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(10)

        # Summary stats
        total = len(configs)
        enabled = sum(1 for c in configs if c.get("enabled", False))
        disabled = total - enabled

        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

        self.set_font("Helvetica", "", 11)
        self.cell(0, 8, f"Total Tests: {total}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 8, f"Enabled: {enabled}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 8, f"Disabled: {disabled}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(10)

        # Test list overview
        if configs:
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 10, "Test Overview", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(3)

            # Table header
            self.set_font("Helvetica", "B", 10)
            self.set_fill_color(230, 230, 230)
            self.cell(80, 8, "Name", border=1, fill=True)
            self.cell(25, 8, "Status", border=1, fill=True, align="C")
            self.cell(35, 8, "Requests", border=1, fill=True, align="C")
            self.cell(35, 8, "Concurrency", border=1, fill=True, align="C")
            self.ln()

            # Table rows
            self.set_font("Helvetica", "", 9)
            for config in configs:
                spec = config.get("spec", {})
                name = config.get("name", "Unknown")
                # Truncate long names
                if len(name) > 35:
                    name = name[:32] + "..."

                status = "Enabled" if config.get("enabled", False) else "Disabled"
                total_requests = spec.get("total_requests", 0)
                concurrency = spec.get("concurrency", 0)

                self.cell(80, 7, name, border=1)
                self.cell(25, 7, status, border=1, align="C")
                self.cell(35, 7, str(total_requests), border=1, align="C")
                self.cell(35, 7, str(concurrency), border=1, align="C")
                self.ln()

    def add_test_section(self, config: dict) -> None:
        """Add a detailed section for a single test."""
        self.add_page()
        spec = config.get("spec", {})

        # Test name as heading
        name = config.get("name", "Unknown Test")
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 12, name, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

        # Status badge
        enabled = config.get("enabled", False)
        self.set_font("Helvetica", "B", 10)
        if enabled:
            self.set_fill_color(200, 255, 200)
            self.cell(30, 7, "ENABLED", border=1, fill=True, align="C")
        else:
            self.set_fill_color(255, 200, 200)
            self.cell(30, 7, "DISABLED", border=1, fill=True, align="C")
        self.ln(12)

        # Description (auto-derived if missing)
        description = derive_description(name, spec.get("description"))
        self.set_font("Helvetica", "I", 10)
        self.multi_cell(0, 6, f"Description: {description}")
        self.ln(5)

        # Target URL and method
        url = spec.get("url", "N/A")
        method = spec.get("method", "GET")
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, "Target", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 10)
        self.cell(0, 6, f"URL: {url}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 6, f"Method: {method}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

        # Load Configuration Table
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, "Load Configuration", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._add_key_value_table([
            ("Total Requests", str(spec.get("total_requests", 100))),
            ("Concurrency", str(spec.get("concurrency", 10))),
            ("Requests/Second", str(spec.get("requests_per_second", "Unlimited"))),
            ("Timeout (seconds)", str(spec.get("timeout_seconds", 30))),
        ])
        self.ln(5)

        # Thresholds Table (if any set)
        thresholds = spec.get("thresholds", {})
        threshold_items = []
        if thresholds.get("max_latency_p50_ms"):
            threshold_items.append(("Max P50 Latency (ms)", str(thresholds["max_latency_p50_ms"])))
        if thresholds.get("max_latency_p95_ms"):
            threshold_items.append(("Max P95 Latency (ms)", str(thresholds["max_latency_p95_ms"])))
        if thresholds.get("max_latency_p99_ms"):
            threshold_items.append(("Max P99 Latency (ms)", str(thresholds["max_latency_p99_ms"])))
        if thresholds.get("max_error_rate") is not None:
            threshold_items.append(("Max Error Rate", f"{thresholds['max_error_rate'] * 100:.1f}%"))
        if thresholds.get("min_throughput_rps"):
            threshold_items.append(("Min Throughput (RPS)", str(thresholds["min_throughput_rps"])))

        if threshold_items:
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 8, "Thresholds", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self._add_key_value_table(threshold_items)
            self.ln(5)

        # Headers (if any)
        headers = spec.get("headers", {})
        if headers:
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 8, "Headers", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            header_items = [(k, v) for k, v in headers.items()]
            self._add_key_value_table(header_items)
            self.ln(5)

        # Endpoints (for multi-endpoint tests)
        endpoints = spec.get("endpoints", [])
        if endpoints:
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 8, "Endpoints", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(2)

            self.set_font("Helvetica", "B", 9)
            self.set_fill_color(230, 230, 230)
            self.cell(40, 7, "Name", border=1, fill=True)
            self.cell(70, 7, "URL", border=1, fill=True)
            self.cell(20, 7, "Method", border=1, fill=True, align="C")
            self.cell(20, 7, "Weight", border=1, fill=True, align="C")
            self.ln()

            self.set_font("Helvetica", "", 8)
            for ep in endpoints:
                ep_name = ep.get("name", "")
                if len(ep_name) > 18:
                    ep_name = ep_name[:15] + "..."
                ep_url = ep.get("url", "")
                if len(ep_url) > 35:
                    ep_url = ep_url[:32] + "..."
                ep_method = ep.get("method", "GET")
                ep_weight = ep.get("weight", 1)

                self.cell(40, 6, ep_name, border=1)
                self.cell(70, 6, ep_url, border=1)
                self.cell(20, 6, ep_method, border=1, align="C")
                self.cell(20, 6, str(ep_weight), border=1, align="C")
                self.ln()
            self.ln(5)

        # Stats
        run_count = config.get("run_count", 0)
        created_at = config.get("created_at")
        updated_at = config.get("updated_at")

        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, "Statistics", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        stats_items = [("Run Count", str(run_count))]
        if created_at:
            stats_items.append(("Created At", str(created_at)[:19]))
        if updated_at:
            stats_items.append(("Updated At", str(updated_at)[:19]))
        self._add_key_value_table(stats_items)

    def _add_key_value_table(self, items: list[tuple[str, str]]) -> None:
        """Add a simple two-column key-value table."""
        self.set_font("Helvetica", "", 10)
        for key, value in items:
            self.set_font("Helvetica", "B", 9)
            self.cell(60, 7, key, border=1)
            self.set_font("Helvetica", "", 9)
            # Truncate long values
            if len(value) > 60:
                value = value[:57] + "..."
            self.cell(100, 7, value, border=1)
            self.ln()


def generate_test_report_pdf(configs: list[dict]) -> bytes:
    """Generate a PDF report of test configurations.

    Args:
        configs: List of test configuration dictionaries with structure:
            - name: str
            - enabled: bool
            - spec: dict (TestSpec fields)
            - created_at: datetime | None
            - updated_at: datetime | None
            - run_count: int

    Returns:
        PDF file content as bytes
    """
    pdf = TestReportPDF()

    # Add summary page
    pdf.add_summary_page(configs)

    # Add detailed section for each test
    for config in configs:
        pdf.add_test_section(config)

    # Output to bytes
    return bytes(pdf.output())
