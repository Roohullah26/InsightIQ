---
title: InsightIQ
emoji: 📊
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
base_path: /dashboard
pinned: false
short_description: AI-powered BI dashboard with TruthLens insights
---

# InsightIQ — AI-Powered Enterprise Business Intelligence Platform

**InsightIQ** is a full-stack, AI-powered Business Intelligence (BI) and automated exploratory data analysis platform built with **FastAPI**, **Pandas**, **NumPy**, **SciPy**, and an interactive **Chart.js** executive web dashboard.

Upload any tabular CSV dataset (or launch the built-in 45-store enterprise benchmark dataset) to immediately synthesize executive briefings, multi-dimensional data health scores, collinear growth clusters, driver correlation matrices, visual group-by aggregations, hybrid outlier inspections, and conversational natural-language data Q&A.

---

## Key Features

### 1. ExecutiveKPI Command Bar & Multi-Dimensional Data Health Score
- **Weighted 100-Point Data Health Model**:
  - **Completeness (`40 pts max`)**: Proportional to valid non-null cells across the dataset matrix.
  - **Sample Adequacy (`30 pts max`)**: Tiered scaling up to `n = 200` (with Central Limit Theorem minimum checks at `n = 30`).
  - **Outlier & Variance Hygiene (`30 pts max`)**: Penalizes features containing extreme statistical anomalies (`-3 pts` per flagged feature, capped at `-15 pts`), duplicate rows, and zero-variance columns.
- **3-Tier Dynamic Sample Adequacy Badges**:
  - `n < 30`: **CLT < 30** (Amber — Critical sample below Central Limit Theorem minimum)
  - `30 <= n < 200`: **SAMPLE < 200** (Cyan/Info — Meets CLT minimum, moderate sample)
  - `n >= 200`: **ROBUST n** (Emerald/Success — Statistically robust for multi-dimensional slicing)
- **Automated Identifier Separation**: Automatically distinguishes primary keys/identifiers (`store_id`, `uuid`, etc.) from true numerical measures and categorical dimensions.

### 2. Seven-Tab Analytical Workspace (Including TruthLens)
1. **TruthLens — 5-Layer Evidence-Based Intelligence Engine**:
   - Identifies situations where business dashboards and headline KPIs are mathematically accurate on the surface but misleading underneath.
   - **8 Core Detection Categories**:
     - *KPI Contradictions* (e.g., Revenue `+40%` while Gross Profit `-20%`; Satisfaction rising while Churn doubles)
     - *Hidden Segment Declines* (e.g., Aggregate revenue `+10%` masking declines in 2 of 3 categories)
     - *Sampling & Response Bias* (e.g., `-82%` collapse in survey participation; sub-CLT segment counts)
     - *Misleading Averages* (Outlier-distorted means vs. medians and trimmed means)
     - *Incomplete Comparisons* (Unnormalized segment totals across unequal population sizes)
     - *Data Quality Problems* (Missing values, duplicate records, structural gaps)
     - *Correlation vs. Causation* (Observational collinearity vs. controlled holdout proof)
     - *Statistical Anomalies* (Hybrid IQR & Z-Score spikes and drops)
   - Includes one-click **Context-Preserving Benchmark Validation Scenarios (Scenarios A, B, and C)**, **Severity & Category Filters**, **7-Section Expandable Insight Cards**, **Dataset Trace & Lineage View**, **Insufficient Evidence Guardrails**, and an interactive **Evidence & Chart Inspector Modal**.
2. **AI Executive Insights**:
   - Synthesizes an **Executive Strategic Briefing** with one-click **Copy Summary**, **Export Word (`.docx`)**, and **Export PDF** report generation.
   - Detects **Multi-Driver Growth Clusters** (maximal cliques with `|r| >= 0.85`), bivariate **Driver Relationships** ordered by business causal hierarchy, **Category Concentration Risks**, and **Statistical Anomalies** with directional recommendations (upper-bound campaign spikes vs. lower-bound service dips).
3. **Talk to Your Data (Dual-Engine Conversational BI)**:
   - Supports both **Deterministic Quantitative Queries** (sums, averages, extrema, grouped rankings, filtered slices) and **Strategic Reasoning** (SWOT analysis, executive 30-day action plans, pareto concentration, root-cause diagnostics, and forecasting hypotheses).
   - Auto-renders inline charts and markdown tables inside the chat stream.
4. **Exploratory Profile**:
   - Column-by-column statistical profiling (mean, standard deviation, min/median/max, IQR, missingness, cardinality, and top frequent values) plus a modal **Schema & Raw Data Head Preview**.
5. **Driver Correlations**:
   - Pairwise **Pearson (`r`)** and **Spearman (`ρ`)** correlation matrices, explained-variance (`R²`) badges, strength meters, an N×N heatmap, and scaled linear regression slope equations.
6. **Visual Aggregations**:
   - Interactive **Horizontal Bar**, **Vertical Bar**, **Line / Trend**, and **Doughnut** charts with `Sum`, `Mean`, `Median`, `Min`, and `Max` aggregations and sorting controls (`Highest First`, `Lowest First`, `Alphabetical`).
   - Always aggregates across **100% of groups** (totals, shares, and means are never truncated); bar charts cap at the Top 15 for readability and donuts bucket the tail into `Top 6 + Other`. Bar charts start at a zero baseline and show a dashed group-mean line.
   - A live, scrollable **Aggregation Breakdown** table (record count, exact value, % share, % delta vs. mean) with **Copy Table** and **Export CSV**.
7. **Anomaly Inspector**:
   - **Hybrid (IQR + Z-Score)**, **IQR (`1.5x` fence)**, and **Z-Score (`|z| > 2.5`)** outlier detection.
   - A clickable per-feature summary strip, an IQR/outlier distribution banner, and a 6-column results table (row, entity context, observed value, bounds, breach delta, z-score/severity) with an inline drawer comparing the full record to column averages.

---

## Project Structure

```text
InsightIQ/
├── app/
│   ├── api/
│   │   ├── routes.py                 # Root & v1 health/readiness probes
│   │   └── v1/
│   │       ├── router.py             # API v1 router aggregator
│   │       └── endpoints/
│   │           ├── datasets.py       # CSV upload, listing, profile, and deletion
│   │           ├── analytics.py      # Correlations, group-by aggregations, and outliers
│   │           ├── insights.py       # Automated executive insights & health scoring
│   │           ├── query.py          # Natural-language Q&A and dynamic query chips
│   │           └── truthlens.py      # TruthLens 5-layer intelligence & scenario endpoints
│   ├── core/
│   │   └── config.py                 # Pydantic Settings & environment variable validation
│   ├── schemas/                      # Pydantic v2 request/response models (including truthlens.py)
│   ├── services/
│   │   ├── column_roles.py           # Identifier vs. measure vs. dimension classifier
│   │   ├── dataset_service.py        # Safe CSV ingestion, caching, and profiling
│   │   ├── analytics_service.py      # Correlation, aggregation, and outlier engines
│   │   ├── insights_service.py       # Collinear clustering & strategic insight synthesis
│   │   ├── query_service.py          # Deterministic NL query & strategic reasoning engine
│   │   └── truthlens_service.py      # 5-layer TruthLens evidence & lineage engine
│   ├── static/
│   │   ├── index.html                # Executive BI dashboard template
│   │   ├── dashboard.css             # Responsive dark-glassmorphism design system
│   │   └── dashboard.js              # Frontend state, Chart.js rendering, and .docx/PDF export
│   └── main.py                       # FastAPI application factory & middleware
├── data/
│   └── executive_q3_performance_45.csv  # 45-row enterprise benchmark dataset
├── tests/                            # Unit & integration tests (pytest)
├── main.py                           # ASGI entry-point shim
├── pyproject.toml                    # Pytest configuration
├── requirements.txt                  # Pinned Python dependencies
└── .env.example                      # Environment configuration template
```

---

## Quickstart

### 1. Prerequisites
- **Python 3.11+**

### 2. Installation
Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configuration (Optional)
InsightIQ runs out of the box with sensible defaults. To customize limits or enable external Gemini LLM synthesis, copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Available environment variables (prefixed with `INSIGHTIQ_`):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `INSIGHTIQ_APP_NAME` | `InsightIQ API` | Service display name |
| `INSIGHTIQ_ENVIRONMENT` | `development` | `development`, `staging`, or `production` |
| `INSIGHTIQ_DEBUG` | `false` | Enables debug mode and auto-reload |
| `INSIGHTIQ_MAX_UPLOAD_SIZE_BYTES` | `10485760` (10 MB) | Maximum allowed CSV upload size |
| `INSIGHTIQ_MAX_ROWS_LIMIT` | `100000` | Maximum rows ingested per dataset |
| `INSIGHTIQ_MAX_COLUMNS_LIMIT` | `200` | Maximum columns ingested per dataset |
| `INSIGHTIQ_AI_ENABLED` | `false` | Toggle external LLM API integration |
| `INSIGHTIQ_AI_MODEL` | `gemini-3.6-flash` | Target Gemini model identifier |
| `INSIGHTIQ_CORS_ORIGINS` | `["*"]` | JSON list of allowed origins. Restrict this in production; credentials are only enabled when `*` is not used |

### 4. Run the Live Server
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive BI Dashboard**: http://127.0.0.1:8000/dashboard
- **Swagger UI (OpenAPI Docs)**: http://127.0.0.1:8000/docs
- **Health Probe**: http://127.0.0.1:8000/health

---

## REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/dashboard` | Serves the interactive InsightIQ web dashboard |
| `GET` | `/health` | Service liveness and version metadata |
| `POST` | `/api/v1/datasets/upload` | Ingests, validates, and profiles a CSV file |
| `GET` | `/api/v1/datasets` | Lists all ingested datasets (deduplicated by newest upload) |
| `GET` | `/api/v1/datasets/{dataset_id}` | Returns full column-level exploratory profile and 5-row head preview |
| `DELETE` | `/api/v1/datasets/{dataset_id}` | Deletes a dataset and cleans up shadowed duplicates |
| `GET` | `/api/v1/insights/{dataset_id}` | Generates executive summary, 40/30/30 health score, and insight cards |
| `GET` | `/api/v1/analytics/correlations/{dataset_id}` | Computes Pearson or Spearman correlation matrix |
| `POST` | `/api/v1/analytics/aggregate/{dataset_id}` | Computes grouped aggregations (`sum`, `mean`, `median`, `min`, `max`, `count`) |
| `GET` | `/api/v1/analytics/outliers/{dataset_id}` | Detects column anomalies via `hybrid`, `iqr`, or `zscore`; each outlier includes its full row, signed z-score, and the column mean |
| `POST` | `/api/v1/query/{dataset_id}` | Answers natural-language quantitative or strategic questions |
| `GET` | `/api/v1/query/{dataset_id}/suggestions` | Returns schema-tailored quick metric chips for the active dataset |
| `GET` | `/api/v1/truthlens/{dataset_id}` | Runs the 5-layer TruthLens engine on a dataset |
| `GET` | `/api/v1/truthlens/scenarios` | Lists the 3 mandatory TruthLens benchmark scenarios (A, B, and C) |
| `GET` | `/api/v1/truthlens/scenarios/{scenario_key}/report` | Evaluates Scenario A, B, or C in memory without altering the active workspace dataset |
| `POST` | `/api/v1/truthlens/scenarios/{scenario_key}` | Ingests and analyzes a TruthLens benchmark scenario (`scenario_a`, `scenario_b`, `scenario_c`) |

---

## Running the Test Suite

Run all unit and API integration tests via `pytest`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

