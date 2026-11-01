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


def test_dashboard_unified_toolbar_and_above_the_fold_workspace():
    """Verify GET /dashboard renders unified control bar, collapsible dropzone, and action buttons."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    content = response.text
    assert "toolbar-bar" in content
    assert "dataset-picker" in content
    assert "toggle-upload-btn" in content
    assert "load-demo-btn" in content
    assert "open-schema-btn" in content
    assert "delete-dataset-btn" in content
    assert "dropzone-collapsible" in content


def test_dashboard_enriched_kpi_elements_and_schema_dialog():
    """Verify GET /dashboard renders enriched KPI elements, tooltips, and schema dialog."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    content = response.text
    assert "health-breakdown-tooltip" in content
    assert "score-completeness" in content
    assert "score-sample" in content
    assert "kpi-rows-badge" in content
    assert "schema-dialog" in content
    assert "schema-columns-table" in content
    assert "schema-preview-table" in content


def test_dashboard_tabs_and_briefing_actions():
    """Verify GET /dashboard renders actionable tab badges and strategic briefing copy/export buttons."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    content = response.text
    assert "badge-insights" in content
    assert "badge-ai" in content
    assert "badge-anomalies" in content
    # Static/non-actionable tab badges removed to prevent collisions
    assert "badge-profile" not in content
    assert "badge-correlations" not in content
    assert "badge-aggregations" not in content
    assert "copy-summary-btn" in content
    assert "export-word-btn" in content
    assert "export-briefing-btn" in content
    assert ".docx" in content


def test_dashboard_ui_bugfixes():
    """Verify UI elements for clear-chat, dynamic chips container, hidden scrollbar, and completeness logic."""
    html_res = client.get("/dashboard")
    assert html_res.status_code == 200
    html = html_res.text
    assert "clear-chat-btn" in html
    assert "quick-metrics-chips" in html

    css_res = client.get("/static/dashboard.css")
    assert css_res.status_code == 200
    css = css_res.text
    assert "scrollbar-width: none" in css
    assert "rgba(11, 15, 25, 0.92)" in css
    assert "chat-md-table" in css
    assert "chat-chart-card" in css
    assert "chat-action-btn" in css

    js_res = client.get("/static/dashboard.js")
    assert js_res.status_code == 200
    js = js_res.text
    assert "formatCompleteness" in js
    assert "loadQuickMetricChips" in js
    assert "resetChat" in js
    assert "renderChatInlineChart" in js


def test_dashboard_kpi_grid_aggregations_and_anomalies_ux():
    """Verify 4-column desktop KPI grid, Anomalies Flagged card, chart types, sort selector, and anomaly logic."""
    html_res = client.get("/dashboard")
    assert html_res.status_code == 200
    html = html_res.text
    assert "kpi-card-anomalies" in html
    assert "Anomalies Flagged" in html
    assert "kpi-anomalies" in html
    assert "agg-chart-type" in html
    assert "agg-sort-select" in html
    assert "agg-chart-title" in html
    assert "anomaly-method-select" in html
    assert 'value="hybrid"' in html

    css_res = client.get("/static/dashboard.css")
    assert css_res.status_code == 200
    css = css_res.text
    assert "repeat(4, minmax(0, 1fr))" in css
    assert "repeat(2, 1fr)" in css
    assert "white-space: nowrap" in css
    assert "toolbar-actions" in css

    js_res = client.get("/static/dashboard.js")
    assert js_res.status_code == 200
    js = js_res.text
    assert "formatHealthScore" in js
    assert "ID" in js
    assert "populateAggregationSelectors" in js
    assert "renderAggChart" in js
    assert "PALETTE" in js
    assert "scanAnomalies" in js
    assert "hybrid" in js
    assert "IQR & Z-Score" in js


def test_dashboard_layout_scaling_and_demo_dataset_upgrades():
    """Verify 4-column KPI row, expanded dataset dropdown, isolated delete button, flex tab navigation, and 45-row demo dataset."""
    html_res = client.get("/dashboard")
    assert html_res.status_code == 200
    html = html_res.text
    # Subtle demo dataset badge/trigger text
    assert "Demo Dataset" in html
    assert "demo-status-badge" in html
    # AI tab badge
    assert "badge-ai" in html
    assert ">AI<" in html
    # 6 tabs present
    assert 'data-tab="tab-insights"' in html
    assert 'data-tab="tab-chat"' in html
    assert 'data-tab="tab-profile"' in html
    assert 'data-tab="tab-correlations"' in html
    assert 'data-tab="tab-aggregations"' in html
    assert 'data-tab="tab-anomalies"' in html

    css_res = client.get("/static/dashboard.css")
    assert css_res.status_code == 200
    css = css_res.text
    # 1. Dataset selector bar expansion & isolated delete button
    assert "flex-wrap: wrap;" in css
    assert "gap: 12px;" in css
    assert "min-width: 340px;" in css
    assert "width: auto;" in css
    assert "margin-left: auto;" in css
    assert "gap: 10px;" in css
    # 2. KPI grid 4 columns on desktop (>=900px), 2 on tablet (<=899px), 1 on mobile (600px)
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in css
    assert "@media (min-width: 900px)" in css
    assert "grid-template-columns: repeat(2, 1fr)" in css
    assert "@media (max-width: 600px)" in css
    assert "gap: 16px;" in css
    assert "white-space: normal;" in css
    # 3. Horizontal flex tab navigation with compact button padding & hidden scrollbar
    assert "padding: 0.55rem 0.85rem;" in css
    assert "font-size: 0.82rem;" in css
    assert "scrollbar-width: none;" in css
    assert "justify-content: center;" in css
    assert "gap: 8px;" in css

    js_res = client.get("/static/dashboard.js")
    assert js_res.status_code == 200
    js = js_res.text
    # Recalibrated 4-tier sample size badges, Title Case insight titles, split health subtext & .docx Word export
    assert "Critical Sample (n &lt; 30)" in js
    assert "Small Sample (CLT Min)" in js
    assert "Moderate Sample" in js
    assert "Optimal Sample" in js
    assert "formatInsightCardTitle" in js
    assert "subtext-positive" in js
    assert "subtext-penalty" in js
    assert "#38bdf8" in js
    assert '<span class="kpi-tag warning">Flagged</span>' in js
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in js
    assert "syncInsightsAndHealthScore" in js
    # 45-row realistic enterprise demo generator with 2 seeded outliers
    assert "45-Row Realistic Enterprise Demo Dataset Generator" in js
    assert "Chicago Flagship" in js
    assert "Honolulu Palm" in js
    assert "Detroit Central,106700.0,16900.0,1073,3.20" in js
    assert "Los Angeles Century,185900.0,37500.0,1892,4.42" in js
    assert "executive_q3_performance.csv" in js


def test_dashboard_chart_toolbar_and_formatting():
    """Verify compact 1-row visual aggregations toolbar, Title Case dropdowns, chart title, and direct bar labels."""
    html_res = client.get("/dashboard")
    assert html_res.status_code == 200
    html = html_res.text
    assert "agg-controls-grid" in html
    assert "agg-control-group" in html
    assert "agg-control-label" in html
    assert "agg-chart-title" in html
    assert 'value="desc" selected' in html
    assert "run-agg-btn" not in html

    css_res = client.get("/static/dashboard.css")
    assert css_res.status_code == 200
    css = css_res.text
    assert "grid-template-columns: repeat(5, minmax(0, 1fr))" in css
    assert "agg-control-label" in css
    assert "font-size: 11px;" in css
    assert ".agg-chart-title" in css
    assert "font-size: 1rem;" in css

    js_res = client.get("/static/dashboard.js")
    assert js_res.status_code == 200
    js = js_res.text
    assert "formatColumnLabel" in js
    assert "humanizeAggTitle" in js
    assert "formatCompactNumber" in js
    assert "directBarValueLabels" in js
    assert "legend: { display: false }" in js
    assert "renderAggChart" in js





