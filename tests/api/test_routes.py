"""Tests for API routes."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Test health check returns OK."""
        response = await async_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data


class TestRunsEndpoints:
    """Tests for runs endpoints."""

    @pytest.mark.asyncio
    async def test_create_run(self, async_client: AsyncClient, sample_test_spec: dict):
        """Test creating a new run."""
        response = await async_client.post(
            "/api/v1/runs",
            json={"spec": sample_test_spec},
        )

        assert response.status_code == 202
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_runs_empty(self, async_client: AsyncClient):
        """Test listing runs when empty."""
        response = await async_client.get("/api/v1/runs")

        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_runs_after_create(
        self, async_client: AsyncClient, sample_test_spec: dict
    ):
        """Test listing runs after creating one."""
        # Create a run
        create_response = await async_client.post(
            "/api/v1/runs",
            json={"spec": sample_test_spec},
        )
        assert create_response.status_code == 202
        run_id = create_response.json()["id"]

        # List runs
        list_response = await async_client.get("/api/v1/runs")

        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] >= 1
        assert any(r["id"] == run_id for r in data["runs"])

    @pytest.mark.asyncio
    async def test_get_run(self, async_client: AsyncClient, sample_test_spec: dict):
        """Test getting a specific run."""
        # Create a run
        create_response = await async_client.post(
            "/api/v1/runs",
            json={"spec": sample_test_spec},
        )
        run_id = create_response.json()["id"]

        # Get the run
        get_response = await async_client.get(f"/api/v1/runs/{run_id}")

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == run_id
        assert data["spec"]["name"] == sample_test_spec["name"]

    @pytest.mark.asyncio
    async def test_get_run_not_found(self, async_client: AsyncClient):
        """Test getting a non-existent run."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(f"/api/v1/runs/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_run_not_found(self, async_client: AsyncClient):
        """Test cancelling a non-existent run."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.post(f"/api/v1/runs/{fake_id}/cancel")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_runs_with_filter(
        self, async_client: AsyncClient, sample_test_spec: dict
    ):
        """Test listing runs with status filter."""
        # Create a run
        await async_client.post(
            "/api/v1/runs",
            json={"spec": sample_test_spec},
        )

        # Filter by completed status (should be empty or different)
        response = await async_client.get("/api/v1/runs?status=completed")

        assert response.status_code == 200
        data = response.json()
        # All returned runs should be completed
        for run in data["runs"]:
            assert run["status"] == "completed"


class TestAuthentication:
    """Tests for API authentication."""

    @pytest.mark.asyncio
    async def test_no_auth_in_dev_mode(self, async_client: AsyncClient, sample_test_spec: dict):
        """Test requests work without auth when no key is configured."""
        # No API key configured (dev mode)
        response = await async_client.post(
            "/api/v1/runs",
            json={"spec": sample_test_spec},
        )

        # Should succeed in dev mode
        assert response.status_code == 202
