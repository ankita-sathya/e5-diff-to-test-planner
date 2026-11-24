"""
E5 Diff-to-Test Planner - Next.js Integration Tests
Tests that the web API correctly integrates with the Python backend.
"""

import json
import pytest
from pathlib import Path
from src.api import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Create a test client for the FastAPI app."""
    monkeypatch.setenv("E5_MOCK_EMBEDDINGS", "1")
    monkeypatch.setattr("src.api._planner", None)
    return TestClient(app)


@pytest.fixture
def sample_diff():
    """Load sample diff for testing."""
    sample_path = Path(__file__).parent.parent / "data" / "sample_pr_diff.patch"
    with open(sample_path) as f:
        return f.read()


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test that health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAnalysisEndpoint:
    """Test the main analysis endpoint."""

    def test_analyze_diff_success(self, client, sample_diff):
        """Test successful diff analysis."""
        request_data = {
            "diff_content": sample_diff,
        }

        response = client.post("/api/analyze", json=request_data)
        assert response.status_code == 200

        data = response.json()

        # Verify response structure
        assert "ranked_tests" in data
        assert "total_hil_time_seconds" in data
        assert "hil_time_saved_seconds" in data
        assert "gap_tickets" in data

        # Verify test ranking is a list
        assert isinstance(data["ranked_tests"], list)

    def test_analyze_diff_missing_content(self, client):
        """Test that missing diff content returns 400."""
        request_data = {
            "diff_content": "",
        }

        response = client.post("/api/analyze", json=request_data)
        assert response.status_code == 400

    def test_analyze_with_custom_thresholds(self, client, sample_diff):
        """Test analysis with custom thresholds."""
        request_data = {
            "diff_content": sample_diff,
            "high_threshold": 0.85,
            "medium_threshold": 0.70,
            "gap_threshold": 0.60,
        }

        response = client.post("/api/analyze", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["ranked_tests"], list)

    def test_thresholds_control_selection_and_are_request_local(self, client, sample_diff):
        selected = client.post("/api/analyze", json={
            "diff_content": sample_diff, "high_threshold": 0.0, "medium_threshold": 0.0,
        })
        assert len(selected.json()["ranked_tests"]) > 0
        strict = client.post("/api/analyze", json={
            "diff_content": sample_diff, "high_threshold": 1.0, "medium_threshold": 1.0,
        })
        assert strict.json()["ranked_tests"] == []
        invalid = client.post("/api/analyze", json={
            "diff_content": sample_diff, "high_threshold": 0.2, "medium_threshold": 0.8,
        })
        assert invalid.status_code == 400

    def test_analyze_with_defect_description(self, client, sample_diff):
        """Test analysis combined with defect description."""
        request_data = {
            "diff_content": sample_diff,
            "defect_description": "Japanese kanji truncation on cluster display",
        }

        response = client.post("/api/analyze", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["gap_tickets"], list)


class TestSampleDataEndpoints:
    """Test endpoints that serve sample data."""

    def test_get_sample_diff(self, client):
        """Test retrieving sample diff."""
        response = client.get("/api/sample-diff")
        assert response.status_code == 200

        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 0
        assert "---" in data["content"] or "+++" in data["content"]

    def test_get_sample_catalog(self, client):
        """Test retrieving sample catalog."""
        response = client.get("/api/sample-catalog")
        assert response.status_code == 200

        data = response.json()
        # Should be a list of test cases
        assert isinstance(data, (list, dict))


class TestResponseFormats:
    """Test that response formats are correct."""

    def test_response_json_serializable(self, client, sample_diff):
        """Test that response can be serialized to JSON."""
        request_data = {
            "diff_content": sample_diff,
        }

        response = client.post("/api/analyze", json=request_data)
        assert response.status_code == 200

        # Should be JSON serializable
        data = response.json()
        json_str = json.dumps(data)
        assert len(json_str) > 0

    def test_response_has_required_fields(self, client, sample_diff):
        """Test that response has all required top-level fields."""
        request_data = {
            "diff_content": sample_diff,
        }

        response = client.post("/api/analyze", json=request_data)
        data = response.json()

        required_fields = [
            "ranked_tests",
            "total_hil_time_seconds",
            "hil_time_saved_seconds",
            "full_suite_time_seconds",
            "gap_tickets",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_coverage_gap_fields(self, client, sample_diff):
        """Test that coverage gaps have all required fields."""
        request_data = {
            "diff_content": sample_diff,
        }

        response = client.post("/api/analyze", json=request_data)
        data = response.json()

        required_fields = {
            "domain": str,
            "similarity_max": (int, float),
            "title": str,
            "gap_reason": str,
            "hil_bench_tags": list,
            "test_steps": list,
        }

        assert data["gap_tickets"]
        for gap in data.get("gap_tickets", []):
            for field, expected_type in required_fields.items():
                assert field in gap, f"Missing field in gap: {field}"
                if expected_type is not list:
                    assert isinstance(gap[field], expected_type), f"Wrong type for {field}"
                else:
                    assert isinstance(gap[field], list)
                    for tag in gap[field]:
                        assert isinstance(tag, str)
