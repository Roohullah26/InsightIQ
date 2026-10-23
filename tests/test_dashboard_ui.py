"""Tests for the InsightIQ interactive dashboard UI and static asset serving."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_dashboard_endpoint_returns_html():
    """Verify GET /dashboard returns HTTP 200 and loads the dashboard HTML template."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    content = response.text
    assert "InsightIQ" in content
    assert "agg-chart" in content
    assert "chat-history" in content
    assert "file-input" in content


def test_static_css_assets_served():
    """Verify dashboard.css is served with correct CSS MIME type."""
    response = client.get("/static/dashboard.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")
    assert "--accent-primary" in response.text


def test_static_js_assets_served():
    """Verify dashboard.js is served with correct JavaScript MIME type."""
    response = client.get("/static/dashboard.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "")
    assert "activeDatasetId" in response.text


def test_dashboard_includes_open_ended_chat_chips():
    """Verify GET /dashboard renders open-ended questioning chips and dual-engine badge."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    content = response.text
    assert "Strategic Reasoning:" in content
    assert "SWOT analysis" in content
    assert "Dual-Engine Intelligence" in content
    assert "suggestion-chip strategic" in content

