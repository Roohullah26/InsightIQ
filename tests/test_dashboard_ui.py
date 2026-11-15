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
    assert "header-command-bar" in content
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


def test_dashboard_v2_command_bar_bento_kpis_and_truthlens_cards():
    """Verify single-row command bar, KPI micro-visuals, segmented tabs, and scannable TruthLens card UI."""
    html = client.get("/dashboard").text
    assert "header-zone-left" in html
    assert "header-zone-center" in html
    assert "header-zone-right" in html
    assert "kpi-health-bar" in html
    assert "kpi-cols-bar" in html
    assert "truthlens-audit-banner" in html
    assert "toolbar-overflow-menu" in html
    # Legacy dataset-wide trace table is no longer user-visible
    assert 'id="truthlens-trace-panel" style="display:none;"' in html

    css = client.get("/static/dashboard.css").text
    assert "height: 64px;" in css
    assert "rgba(11, 15, 25, 0.8)" in css
    assert "grid-template-columns: 1.15fr 0.85fr;" in css
    assert "font-variant-numeric: tabular-nums;" in css
    assert "JetBrains Mono" in css
    assert "background: #090d16;" in css
    assert "kpi-meter" in css
    assert "kpi-stack-bar" in css

    js = client.get("/static/dashboard.js").text
    assert "buildTruthLensEvidenceGrid" in js
    assert "buildLineagePill" in js
    assert "renderTruthLensAuditBanner" in js
    assert "tl-hyp-next" in js
    assert "slice(0, 5)" not in js.split("function buildTruthLensEvidenceGrid")[1].split("function buildLineagePill")[0]


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


def test_dashboard_above_the_fold_navbar_dropzone_kpis_and_copilot():
    """Verify single-row 60px navbar, hidden-by-default styled dropzone, uniform 4-col KPI strip, and 2-col Copilot starter grid."""
    html = client.get("/dashboard").text
    assert 'id="dropzone-container" style="display: none;"' in html
    assert 'class="dropzone-left"' in html

    css = client.get("/static/dashboard.css").text
    assert "height: 60px;" in css
    assert "max-width: 360px;" in css
    assert "border: 1px dashed rgba(56, 189, 248, 0.35);" in css
    assert "min-height: 125px;" in css
    assert "max-height: 145px;" in css
    assert "padding: 16px 18px;" in css
    assert "grid-template-columns: 1fr 1fr;" in css
    assert "background: #090D16;" in css
    assert "padding: 6px 6px 6px 16px;" in css

    js = client.get("/static/dashboard.js").text
    assert "dropzoneContainer.style.display = 'none'" in js
    assert 'class="subtext-penalty text-warning" title="' in js


def test_truthlens_v3_footer_radial_glow_microcharts_and_slideover_drawer():
    """Verify deduplicated card footer, radial severity glows, IQR bullet track, segment delta pills, and slide-over visual drawer."""
    html = client.get("/dashboard").text
    assert "tl-slideover-drawer" in html
    assert "tl-dialog-source-table" in html

    css = client.get("/static/dashboard.css").text
    assert ".tl-audit-toggle-btn" in css
    assert "radial-gradient(circle at 0% 0%, rgba(245, 158, 11, 0.12), transparent 35%)" in css
    assert ".tl-bullet-chart" in css
    assert ".tl-bullet-safe-zone" in css
    assert ".tl-bullet-marker" in css
    assert ".tl-delta-pill.pos" in css
    assert ".tl-delta-pill.neg" in css
    assert "width: 520px;" in css
    assert "backdrop-filter: blur(16px);" in css
    assert "background: rgba(11, 15, 25, 0.95);" in css

    js = client.get("/static/dashboard.js").text
    assert "tl-audit-toggle-btn" in js
    assert "tl-bullet-chart" in js
    assert "tl-delta-pill" in js
    assert "rgba(56, 189, 248, 0.18)" in js
    assert "tl-dialog-source-body" in js
    assert "slice(0, 28)" not in js


def test_two_pane_enterprise_app_shell_sidebar_and_briefing_grid():
    """Verify 2-pane app shell, collapsible 250px/64px left sidebar, categorized menu groups, 115px KPI strip, and 2-col briefing cards."""
    html = client.get("/dashboard").text
    assert 'id="app-shell"' in html
    assert 'id="app-sidebar"' in html
    assert 'id="sidebar-collapse-btn"' in html
    assert "AI INTELLIGENCE" in html
    assert "DATA EXPLORATION" in html
    assert "GOVERNANCE &amp; AUDIT" in html
    assert 'id="sidebar-dataset-meta"' in html
    assert 'id="main-workspace"' in html

    css = client.get("/static/dashboard.css").text
    assert "width: 250px;" in css
    assert "width: 64px;" in css
    assert "background: #070A12;" in css
    assert "font-size: 10.5px;" in css
    assert "border-left: 3px solid #38bdf8;" in css
    assert "linear-gradient(90deg, rgba(56, 189, 248, 0.14), rgba(99, 102, 241, 0.04))" in css
    assert "min-height: 115px;" in css
    assert ".insight-evidence-pillbar" in css
    assert ".insight-recommendation-box" in css

    js = client.get("/static/dashboard.js").text
    assert "sidebar-collapse-btn" in js
    assert "insight-card-full" in js
    assert "insight-evidence-pillbar" in js
    assert "insight-recommendation-box" in js


def test_above_the_fold_v4_kpi_row_sidebar_footer_collapsible_audit_and_toolbar():
    """Verify 1x4 KPI strip (>= 960px), compact 24px KPI metric & CLT < 30 badge, unified sidebar footer, collapsible Dataset Audit Summary, 2-row TruthLens toolbar, and Cross-Tabulation Sparsity Risk hypothesis."""
    html = client.get("/dashboard").text
    assert "sidebar-group-header-top" in html
    assert "sidebar-unified-pill" in html
    assert "API Online v0.1.0" in html
    assert "tl-toolbar-row-primary" in html
    assert "tl-toolbar-row-secondary" in html

    css = client.get("/static/dashboard.css").text
    assert "@media (min-width: 960px)" in css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr)) !important;" in css
    assert "padding: 12px 14px;" in css
    assert "font-size: 24px;" in css
    assert "height: calc(100vh - 60px);" in css
    assert "font-size: 20px;" in css
    assert ".tl-audit-collapsible" in css
    assert ".tl-audit-summary-strip" in css
    assert ".tl-toolbar-row-primary" in css
    assert ".tl-toolbar-row-secondary" in css

    js = client.get("/static/dashboard.js").text
    assert "CLT &lt; 30" in js
    assert "tl-audit-collapsible" in js
    assert "View Audit Metadata" in js
    assert "Cross-Tabulation Sparsity Risk" in js
    assert "Pool multi-period records before running multi-dimensional cross-tabulations." in js


def test_exploratory_profile_and_kpi_typography_v5():
    """Verify concise KPI titles (10.5px), 11.5px subtitles, dynamic SAMPLE < 200 / ROBUST n badges, preview table header bar & outlier pills, and 3-col feature profile cards with 6px mini-bars."""
    html = client.get("/dashboard").text
    assert '>Data Health<' in html
    assert '>Total Records<' in html
    assert '>Features<' in html
    assert '>Anomalies<' in html
    assert 'id="preview-table-toolbar"' in html
    assert "Sample Records Preview (Top 5 of 45 rows)" in html
    assert 'id="preview-table-filter"' in html
    assert "◧" not in html

    css = client.get("/static/dashboard.css").text
    assert "font-size: 10.5px;" in css
    assert "letter-spacing: 0.05em;" in css
    assert "font-size: 11.5px;" in css
    assert "padding: 10px 14px;" in css
    assert "font-size: 13px;" in css
    assert ".preview-outlier-pill" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in css
    assert "gap: 14px;" in css
    assert ".col-mini-bar-track" in css
    assert ".col-mini-bar-mean-dot" in css

    js = client.get("/static/dashboard.js").text
    assert "SAMPLE &lt; 200" in js
    assert "ROBUST n" in js
    assert "formatProfileStatNumber" in js
    assert "Intl.NumberFormat" in js
    assert "preview-outlier-pill" in js
    assert "col-mini-bar-mean-dot" in js


def test_driver_correlations_bento_grid_r2_meter_and_heatmap_v6():
    """Verify 2-column correlation bento grid, R² shared variance badges, 8px tick-marked meter, N×N heatmap matrix, and 2 rows · 2 cols KPI footer."""
    html = client.get("/dashboard").text
    assert "2 rows · 2 cols" in html
    assert 'id="corr-summary-pill"' in html

    css = client.get("/static/dashboard.css").text
    assert ".corr-bento-grid" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css
    assert "padding: 16px 18px;" in css
    assert "linear-gradient(90deg, #0ea5e9, #10b981)" in css
    assert "linear-gradient(90deg, #6366f1, #38bdf8)" in css
    assert ".corr-matrix-panel" in css
    assert ".corr-heatmap-table" in css
    assert ".corr-meter-tick" in css

    js = client.get("/static/dashboard.js").text
    assert "corr-matrix-heatmap" in js
    assert "Numeric Correlation Matrix Heatmap" in js
    assert "shared variance" in js
    assert "STRONG POSITIVE" in js
    assert "MODERATE POSITIVE" in js
    assert "Inspect Scatter &amp; Fit Line →" in js
    assert "openCorrelationScatterPreview" in js


def test_visual_aggregations_zero_baseline_2col_split_and_breakdown_table_v7():
    """Verify unclipped 5-col filter selects, zero-baseline 270px bar chart, dashed mean reference line, 2-decimal precision, and 2-col Chart + Live Breakdown Table."""
    html = client.get("/dashboard").text
    assert 'id="agg-workspace-split"' in html
    assert 'id="agg-chart-subtitle-pill"' in html
    assert 'id="agg-breakdown-table"' in html
    assert 'id="agg-copy-table-btn"' in html
    assert 'id="agg-export-csv-btn"' in html
    assert "Live Aggregation Breakdown" in html

    css = client.get("/static/dashboard.css").text
    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in css
    assert "padding: 8px 28px 8px 12px;" in css
    assert "text-overflow: ellipsis;" in css
    assert "grid-template-columns: 1.45fr 1fr;" in css
    assert "height: 270px;" in css
    assert "max-height: 280px;" in css
    assert ".agg-breakdown-table" in css
    assert ".agg-share-bar-track" in css
    assert ".agg-delta-badge.agg-delta-pos" in css
    assert ".agg-delta-badge.agg-delta-neg" in css

    js = client.get("/static/dashboard.js").text
    assert "beginAtZero: true" in js
    assert "min: 0" in js
    assert "setLineDash([5, 5])" in js
    assert "renderAggBreakdownTable" in js
    assert "copyAggBreakdownTable" in js
    assert "exportAggBreakdownCsv" in js
    assert "rgba(99, 102, 241, 0.35)" in js


def test_anomaly_inspector_enterprise_workbench_v8():
    """Verify Flagged Feature Strip pills, 1-row toolbar, 2-col IQR diagnostic banner, 6-col contextual table, and inline row drawer."""
    html = client.get("/dashboard").text
    assert 'id="anomaly-feature-strip"' in html
    assert 'id="anomaly-feature-pills"' in html
    assert "Load a dataset to see flagged features." in html
    assert "DEMO_FALLBACK_ROWS_BY_INDEX" not in client.get("/static/dashboard.js").text
    assert 'id="anomaly-toolbar-bar"' in html
    assert "INSPECT COLUMN" in html
    assert "DETECTION METHOD" in html

    css = client.get("/static/dashboard.css").text
    assert ".anomaly-feature-strip" in css
    assert ".anomaly-feature-pill.flagged.active" in css
    assert "grid-template-columns: 1fr 1.3fr auto;" in css
    assert "height: 38px;" in css
    assert "padding: 0 20px;" in css
    assert ".anomaly-diagnostic-banner" in css
    assert ".anomaly-iqr-track" in css
    assert "height: 12px;" in css
    assert "background: #090D16;" in css
    assert ".anomaly-workbench-table" in css
    assert ".anomaly-row-context-grid" in css

    js = client.get("/static/dashboard.js").text
    assert "renderAnomalyFeatureStrip" in js
    assert "buildEntityContextLabel" in js
    assert "Lower Bound:" in js
    assert "Column Mean:" in js
    assert "Upper Bound:" in js
    assert "ENTITY / CONTEXT" in js
    assert "NORMAL BOUNDS" in js
    assert "BREACH DELTA" in js
    assert "Z-SCORE / SEVERITY" in js
    assert "Full Record Inspection" in js


def test_visual_aggregations_high_cardinality_donut_and_1x5_strip_v9():
    """Verify strict 1x5 filter strip, 1.15fr/1fr side-by-side split, 310px sticky table, full dataset aggregation (limit 1000), and Top-6 + Other Donut bucketing."""
    html = client.get("/dashboard").text
    assert "◧" not in html

    css = client.get("/static/dashboard.css").text
    assert "grid-template-columns: repeat(5, minmax(0, 1fr)) !important;" in css
    assert "height: 34px !important;" in css
    assert "font-size: 12.5px !important;" in css
    assert "padding: 0 24px 0 10px !important;" in css
    assert "font-size: 10px !important;" in css
    assert "grid-template-columns: 1.15fr 1fr !important;" in css
    assert "max-height: 310px !important;" in css
    assert "position: sticky;" in css
    assert "#header-sidebar-toggle" in css

    js = client.get("/static/dashboard.js").text
    assert "limit: 1000" in js
    assert "Showing Top 15 of" in js
    assert "Full Dataset Total:" in js
    assert "donutCenterMetric" in js
    assert "truncateLegendLabel" in js
    assert "cutout: '66%'" in js
    assert "#475569" in js


def test_aggregations_media_query_overrides_and_donut_legend_share_v10():
    """Verify final overrides keep 1x5 filter bar (>=768px) and side-by-side split (>=860px), 230px canvas, and % share legend."""
    html = client.get("/dashboard").text
    assert "◧" not in html

    css = client.get("/static/dashboard.css").text
    assert "@media (min-width: 768px)" in css
    assert "@media (min-width: 860px)" in css
    assert "grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr) !important;" in css
    assert "height: 32px !important;" in css
    assert "padding: 0 22px 0 8px !important;" in css
    assert "height: 230px !important;" in css
    assert "max-height: 230px !important;" in css
    assert "@media (max-width: 1120px) {\n  .agg-workspace-split" not in css.replace("\r\n", "\n")

    js = client.get("/static/dashboard.js").text
    assert "generateLabels(chart)" in js
    assert "· ${pct.toFixed(1)}%" in js














