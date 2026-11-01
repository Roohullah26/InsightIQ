"""Unit tests for the QueryService natural language question-answering engine."""

import pytest
from app.core.config import Settings
from app.services.dataset_service import DatasetNotFoundError, DatasetService
from app.services.query_service import QueryService


@pytest.fixture
def query_test_setup(tmp_path):
    """Provide isolated Settings and pre-seeded dataset for query engine testing."""
    test_settings = Settings(
        data_dir=tmp_path / "query_data",
        _env_file=None,
    )

    csv_data = (
        "region,store,revenue,profit\n"
        "North,Store_A,1000,200\n"
        "North,Store_B,1500,300\n"
        "South,Store_C,2000,400\n"
        "South,Store_D,2500,500\n"
        "East,Store_E,500,100\n"
        "West,Store_F,10000,2000\n"  # West is top and has outlier
    ).encode("utf-8")

    upload_res = DatasetService.ingest_csv(
        file_bytes=csv_data,
        filename="sales_territory.csv",
        settings=test_settings,
    )

    return test_settings, upload_res.summary.dataset_id


def test_query_general_row_count(query_test_setup):
    """Verify 'how many rows' inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "How many rows are in this dataset?", settings)

    assert res.intent == "general_count"
    assert "6 rows" in res.answer
    assert res.data_preview[0]["row_count"] == 6


def test_query_metric_summary_total_and_average(query_test_setup):
    """Verify total and average metric calculations."""
    settings, dataset_id = query_test_setup

    # Total revenue: 1000 + 1500 + 2000 + 2500 + 500 + 10000 = 17500
    res_sum = QueryService.execute_query(dataset_id, "What is the total revenue?", settings)
    assert res_sum.intent == "metric_summary"
    assert "17,500.00" in res_sum.answer

    # Average profit: (200 + 300 + 400 + 500 + 100 + 2000) / 6 = 583.33
    res_avg = QueryService.execute_query(dataset_id, "What is the average profit?", settings)
    assert res_avg.intent == "metric_summary"
    assert "583.33" in res_avg.answer


def test_query_grouped_aggregation(query_test_setup):
    """Verify 'revenue by region' grouped aggregation inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Show me revenue by region", settings)

    assert res.intent == "grouped_aggregation"
    assert res.target_metric == "revenue"
    assert res.group_by_dimension == "region"
    assert "West" in res.answer
    assert len(res.data_preview) == 4


def test_query_ranking_extreme(query_test_setup):
    """Verify 'top store by revenue' ranking inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "What is the top store by revenue?", settings)

    assert res.intent == "ranking_extreme"
    assert "10,000.00" in res.answer
    assert "Store_F" in res.answer


def test_query_filtered_metric(query_test_setup):
    """Verify 'revenue in North' filtered calculation."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "What is the revenue in North?", settings)

    assert res.intent == "filtered_metric"
    assert "2,500.00" in res.answer  # 1000 + 1500
    assert "North" in res.answer


def test_query_correlation_inquiry(query_test_setup):
    """Verify correlation inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Is there a correlation between revenue and profit?", settings)

    assert res.intent == "correlation_inquiry"
    assert "1.000" in res.answer


def test_query_anomaly_inquiry(query_test_setup):
    """Verify outlier/anomaly inquiry."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Are there any outliers in revenue?", settings)

    assert res.intent == "anomaly_inquiry"
    assert "10,000.00" in res.answer


def test_query_nonexistent_dataset_raises_not_found(query_test_setup):
    """Verify querying non-existent dataset ID raises DatasetNotFoundError."""
    settings, _ = query_test_setup
    with pytest.raises(DatasetNotFoundError):
        QueryService.execute_query("unknown_uuid", "total revenue", settings)


def test_query_open_ended_swot_analysis(query_test_setup):
    """Verify SWOT analysis inquiry returns rich structured grounded answer."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Give me a SWOT analysis of this business data", settings)

    assert res.intent == "open_ended_reasoning"
    assert res.source == "deterministic_engine"
    assert "SWOT Analysis" in res.answer
    assert "Strengths:" in res.answer
    assert "Weaknesses:" in res.answer
    assert "Opportunities:" in res.answer
    assert "Threats" in res.answer
    assert res.data_preview is not None
    assert any(row["metric"] == "Total Records" for row in res.data_preview)


def test_query_open_ended_strategic_recommendations(query_test_setup):
    """Verify strategic recommendations question generates prioritized actions."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "What strategic recommendations do you suggest to improve performance?", settings)

    assert res.intent == "open_ended_reasoning"
    assert res.source == "deterministic_engine"
    assert "Strategic Recommendations" in res.answer
    assert "Priority 1" in res.answer
    assert "Priority 2" in res.answer


def test_query_open_ended_why_causal_analysis(query_test_setup):
    """Verify 'why' question generates causal driver analysis."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Why is profit lower in certain stores?", settings)

    assert res.intent == "open_ended_reasoning"
    assert res.source == "deterministic_engine"
    assert "Factor & Causal Driver Analysis" in res.answer
    assert "variance" in res.answer.lower() or "concentration" in res.answer.lower()


def test_query_open_ended_investor_briefing(query_test_setup):
    """Verify investor/pitch inquiry generates executive briefing."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "What should an investor know about this company?", settings)

    assert res.intent == "open_ended_reasoning"
    assert res.source == "deterministic_engine"
    assert "Investor & Stakeholder Executive Briefing" in res.answer
    assert "Investment Thesis" in res.answer


def test_query_open_ended_eli5_analogy(query_test_setup):
    """Verify 'explain like I'm 5' inquiry generates simplified analogy."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Explain this dataset like I'm 5", settings)

    assert res.intent == "open_ended_reasoning"
    assert res.source == "deterministic_engine"
    assert "Explain Like I'm 5" in res.answer


def test_query_open_ended_general_fallback(query_test_setup):
    """Verify any broad question routes to open-ended reasoning rather than failing."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "Can you share your thoughts and high-level ideas on this data?", settings)

    assert res.intent == "open_ended_reasoning"
    assert res.source == "deterministic_engine"
    assert "Executive Business Intelligence Synthesis" in res.answer


def test_query_unrecognized_gibberish(query_test_setup):
    """Verify uninterpretable gibberish correctly returns unrecognized intent."""
    settings, dataset_id = query_test_setup
    res = QueryService.execute_query(dataset_id, "xyz123abc", settings)

    assert res.intent == "unrecognized"
    assert res.confidence == 0.20


def test_query_gemini_ai_model_integration(query_test_setup, monkeypatch):
    """Verify that when Gemini API is available and succeeds, source is 'ai_model'."""
    settings, dataset_id = query_test_setup
    ai_settings = Settings(
        data_dir=settings.data_dir,
        gemini_api_key="mock-valid-gemini-key",
        _env_file=None,
    )

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "### 🤖 AI Executive Briefing\n\nBased on your revenue numbers, Store F is crushing it."
                                }
                            ]
                        }
                    }
                ]
            }

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def post(self, url, json):
            return MockResponse()

    import httpx
    monkeypatch.setattr(httpx, "Client", MockClient)

    res = QueryService.execute_query(dataset_id, "What strategic advice do you have for this company?", ai_settings)
    assert res.intent == "open_ended_reasoning"
    assert res.source == "ai_model"
    assert "Store F is crushing it" in res.answer
    assert res.confidence >= 0.95


def test_query_gemini_ai_fallback_on_error(query_test_setup, monkeypatch):
    """Verify that when Gemini API raises an exception or returns 500, it falls back gracefully to deterministic engine."""
    settings, dataset_id = query_test_setup
    ai_settings = Settings(
        data_dir=settings.data_dir,
        gemini_api_key="mock-failing-gemini-key",
        _env_file=None,
    )

    class FailingClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def post(self, url, json):
            raise RuntimeError("Gemini API connection timeout")

    import httpx
    monkeypatch.setattr(httpx, "Client", FailingClient)

    res = QueryService.execute_query(dataset_id, "Give me a SWOT analysis of this business data", ai_settings)
    assert res.intent == "open_ended_reasoning"
    assert res.source == "deterministic_engine"
    assert "SWOT Analysis" in res.answer


def test_exclude_identifier_columns_and_prioritize_financial_metrics(tmp_path):
    """Verify Customer ID is detected as identifier and Total Spend is prioritized as primary measure."""
    test_settings = Settings(data_dir=tmp_path / "id_test_data", _env_file=None)
    csv_rows = [
        "Customer ID,Region,Total Spend,Items Purchased\n",
        "101,North,1200.50,4\n",
        "102,North,1500.00,5\n",
        "103,South,800.00,2\n",
        "104,South,950.00,3\n",
        "105,East,3400.00,10\n",
        "106,West,2100.00,7\n",
    ]
    upload_res = DatasetService.ingest_csv(
        file_bytes="".join(csv_rows).encode("utf-8"),
        filename="customers.csv",
        settings=test_settings,
    )
    dataset_id = upload_res.summary.dataset_id

    # 1. Check profile sets is_identifier
    profile = DatasetService.get_dataset_profile(dataset_id=dataset_id, settings=test_settings)
    id_col = next(c for c in profile.columns if c.name == "Customer ID")
    assert id_col.is_identifier is True
    spend_col = next(c for c in profile.columns if c.name == "Total Spend")
    assert spend_col.is_identifier is False

    # 2. Check build_quick_metric_suggestions
    suggestions = QueryService.build_quick_metric_suggestions(dataset_id=dataset_id, settings=test_settings)
    assert suggestions.primary_metric == "Total Spend"
    assert suggestions.primary_dimension == "Region"
    assert "Customer ID" in suggestions.excluded_identifiers
    assert len(suggestions.chips) == 6
    assert "Customer ID" not in suggestions.chips[0]
    assert "Total Spend" in suggestions.chips[0]
    assert "Total Spend by Region" in suggestions.chips[1]
    assert "Total Spend" in suggestions.chips[3]  # outlier chip
    assert "Total Spend" in suggestions.chips[4] and "Items Purchased" in suggestions.chips[4]  # correlation chip
    assert "rows and columns" in suggestions.chips[5]


def test_distinct_intent_handlers(query_test_setup):
    """Verify distinct intent handlers for risks, grouped markdown table, charts, and row/column count."""
    settings, dataset_id = query_test_setup

    # 1. Risks & blind spots handler
    risk_res = QueryService.execute_query(dataset_id, "What are our key risks and blind spots?", settings)
    assert risk_res.intent == "risk_analysis"
    assert "Risks & Blind Spots Analysis" in risk_res.answer
    assert "Executive Business Intelligence Synthesis" not in risk_res.answer

    # 2. Grouped aggregation Markdown table
    grouped_res = QueryService.execute_query(dataset_id, "Show me revenue by region", settings)
    assert grouped_res.intent == "grouped_aggregation"
    assert "| Count | Sum | Mean | % Share |" in grouped_res.answer
    assert grouped_res.action is not None
    assert grouped_res.action["target_tab"] == "tab-aggregations"
    assert grouped_res.action["dimension"] == "region"
    assert grouped_res.action["metric"] == "revenue"

    # 3. Chart request handler
    chart_res = QueryService.execute_query(dataset_id, "Show me the graph for revenue by region", settings)
    assert chart_res.intent == "chart_request"
    assert chart_res.chart is not None
    assert chart_res.chart["type"] == "bar"
    assert len(chart_res.chart["labels"]) > 0
    assert chart_res.action is not None
    assert chart_res.action["target_tab"] == "tab-aggregations"

    # 4. Scatter chart request
    scatter_res = QueryService.execute_query(dataset_id, "Show me scatter plot revenue vs profit", settings)
    assert scatter_res.intent == "chart_request"
    assert scatter_res.chart is not None
    assert scatter_res.chart["type"] == "scatter"
    assert scatter_res.action is not None
    assert scatter_res.action["target_tab"] == "tab-correlations"

    # 5. Row and column count query
    count_res = QueryService.execute_query(dataset_id, "How many rows and columns are in this dataset?", settings)
    assert count_res.intent == "general_count"
    assert "rows and" in count_res.answer and "columns" in count_res.answer


def test_filter_intent_word_boundary_and_stopword_protection(tmp_path):
    """Verify short category codes like 'IN' or 'OR' or substring matches do not hijack general metric queries."""
    settings = Settings(data_dir=tmp_path / "filter_boundary_data", _env_file=None)
    csv_data = (
        "state,channel,revenue\n"
        "IN,Online,1000\n"
        "OR,Retail,2000\n"
        "CA,Online,3000\n"
    ).encode("utf-8")
    res = DatasetService.ingest_csv(csv_data, "states.csv", settings)
    ds_id = res.summary.dataset_id

    # "in" inside "What is the total revenue in general?" must not filter by state=='IN'
    q_res = QueryService.execute_query(ds_id, "What is the total revenue in general?", settings)
    assert q_res.intent == "metric_summary"
    assert "6,000.00" in q_res.answer

    # Substring "line" must not falsely match channel=="Online"
    q_sub = QueryService.execute_query(ds_id, "What is the total revenue baseline?", settings)
    assert q_sub.intent == "metric_summary"
    assert "6,000.00" in q_sub.answer


