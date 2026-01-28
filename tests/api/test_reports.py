"""Tests for PDF report generation."""

import pytest
from httpx import AsyncClient

from api.reports.pdf_generator import derive_description, generate_test_report_pdf


class TestDeriveDescription:
    """Tests for the derive_description helper function."""

    def test_returns_existing_description(self):
        """Test that existing description is returned unchanged."""
        result = derive_description("Test Name", "Existing description")
        assert result == "Existing description"

    def test_derives_from_name_with_hyphens(self):
        """Test derivation from name with hyphens."""
        result = derive_description("Stock-AAPL-Endpoint", None)
        assert result == "Load test for Stock AAPL Endpoint"

    def test_derives_from_name_with_underscores(self):
        """Test derivation from name with underscores."""
        result = derive_description("user_login_test", None)
        assert result == "Load test for user login test"

    def test_derives_from_simple_name(self):
        """Test derivation from simple name."""
        result = derive_description("API Health Check", None)
        assert result == "Load test for API Health Check"

    def test_empty_description_triggers_derivation(self):
        """Test that empty string description triggers derivation."""
        result = derive_description("My Test", "")
        assert result == "Load test for My Test"


class TestGenerateTestReportPdf:
    """Tests for PDF generation."""

    def test_generates_pdf_bytes(self):
        """Test that generate_test_report_pdf returns bytes."""
        configs = [
            {
                "name": "Test API",
                "enabled": True,
                "spec": {
                    "name": "Test API",
                    "url": "https://example.com/api",
                    "method": "GET",
                    "total_requests": 100,
                    "concurrency": 10,
                    "timeout_seconds": 30,
                    "thresholds": {},
                    "headers": {},
                },
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "run_count": 5,
            }
        ]

        result = generate_test_report_pdf(configs)

        assert isinstance(result, bytes)
        assert len(result) > 0
        # PDF files start with %PDF
        assert result[:4] == b"%PDF"

    def test_generates_pdf_with_empty_configs(self):
        """Test PDF generation with no configs."""
        result = generate_test_report_pdf([])

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_generates_pdf_with_multiple_configs(self):
        """Test PDF generation with multiple configs."""
        configs = [
            {
                "name": "Test 1",
                "enabled": True,
                "spec": {
                    "name": "Test 1",
                    "url": "https://example.com/1",
                    "method": "GET",
                    "total_requests": 50,
                    "concurrency": 5,
                },
                "run_count": 1,
            },
            {
                "name": "Test 2",
                "enabled": False,
                "spec": {
                    "name": "Test 2",
                    "url": "https://example.com/2",
                    "method": "POST",
                    "total_requests": 200,
                    "concurrency": 20,
                },
                "run_count": 10,
            },
        ]

        result = generate_test_report_pdf(configs)

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_generates_pdf_with_thresholds(self):
        """Test PDF generation with thresholds set."""
        configs = [
            {
                "name": "Test with Thresholds",
                "enabled": True,
                "spec": {
                    "name": "Test with Thresholds",
                    "url": "https://example.com/api",
                    "method": "GET",
                    "total_requests": 100,
                    "concurrency": 10,
                    "thresholds": {
                        "max_latency_p95_ms": 500,
                        "max_error_rate": 0.01,
                        "min_throughput_rps": 100,
                    },
                },
                "run_count": 0,
            }
        ]

        result = generate_test_report_pdf(configs)

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_generates_pdf_with_endpoints(self):
        """Test PDF generation with multi-endpoint test."""
        configs = [
            {
                "name": "Multi-Endpoint Test",
                "enabled": True,
                "spec": {
                    "name": "Multi-Endpoint Test",
                    "url": "",
                    "method": "GET",
                    "total_requests": 100,
                    "concurrency": 10,
                    "endpoints": [
                        {"name": "Endpoint A", "url": "https://example.com/a", "method": "GET", "weight": 2},
                        {"name": "Endpoint B", "url": "https://example.com/b", "method": "POST", "weight": 1},
                    ],
                },
                "run_count": 3,
            }
        ]

        result = generate_test_report_pdf(configs)

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_generates_pdf_with_headers(self):
        """Test PDF generation with custom headers."""
        configs = [
            {
                "name": "Test with Headers",
                "enabled": True,
                "spec": {
                    "name": "Test with Headers",
                    "url": "https://example.com/api",
                    "method": "GET",
                    "total_requests": 100,
                    "concurrency": 10,
                    "headers": {
                        "Authorization": "Bearer token123",
                        "Content-Type": "application/json",
                    },
                },
                "run_count": 2,
            }
        ]

        result = generate_test_report_pdf(configs)

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"


class TestReportEndpoint:
    """Tests for the /tests/report API endpoint."""

    @pytest.mark.asyncio
    async def test_get_report_empty(self, async_client: AsyncClient):
        """Test getting report with no test configs."""
        response = await async_client.get("/api/v1/tests/report")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_get_report_with_enabled_only(self, async_client: AsyncClient):
        """Test getting report with enabled_only filter."""
        response = await async_client.get("/api/v1/tests/report?enabled_only=true")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_get_report_after_run(
        self, async_client: AsyncClient, sample_test_spec: dict
    ):
        """Test getting report after creating a test run."""
        # Create a run to generate a test config
        create_response = await async_client.post(
            "/api/v1/runs",
            json={"spec": sample_test_spec},
        )
        assert create_response.status_code == 202

        # Get the report
        response = await async_client.get("/api/v1/tests/report")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content[:4] == b"%PDF"
        # Report should be larger than empty one since it has test data
        assert len(response.content) > 1000

    @pytest.mark.asyncio
    async def test_report_content_disposition(self, async_client: AsyncClient):
        """Test that report has correct Content-Disposition header."""
        response = await async_client.get("/api/v1/tests/report")

        assert response.status_code == 200
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert "test-report.pdf" in response.headers["content-disposition"]
